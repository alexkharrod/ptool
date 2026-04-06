"""
PromoStandards API client for LogoIncluded.

Endpoints (from PromoStandards public directory for company code "logoincluded"):
  ProductData:  https://productdata.logoincluded.com/ProductData.svc
  MediaContent: https://mediacontent.logoincluded.com/MediaContent.svc  (broken server-side)
  PPC:          https://productprice.logoincluded.com/ProductPrice.svc

Namespace pattern (dual-namespace, document/literal):
  - Wrapper element uses the main service namespace with explicit prefix
  - All child fields (wsVersion, id, password, etc.) use the SharedObjects sub-namespace
  This matches the XSD schema which uses ref="ns3:fieldName" for every child element.

Usage:
    from products.promostandards import PromoStandardsClient
    client = PromoStandardsClient()
    products = client.get_sellable_products()
    detail = client.get_product("EC18")
    pricing = client.get_pricing("EC18", "EC18_Black")
"""

import xml.etree.ElementTree as ET

import requests

# ── Credentials ────────────────────────────────────────────────────────────────
PS_USERNAME = "alexkharrod@gmail.com"
PS_PASSWORD = "REDACTED"

# ── Endpoints ──────────────────────────────────────────────────────────────────
PRODUCT_DATA_URL = "https://productdata.logoincluded.com/ProductData.svc"
PPC_URL          = "https://productprice.logoincluded.com/ProductPrice.svc"
# MEDIA_CONTENT_URL — server-side 115 error on all requests; skipped

# ── Namespaces ─────────────────────────────────────────────────────────────────
NS_PS     = "http://www.promostandards.org/WSDL/ProductDataService/2.0.0/"
NS_PS_SO  = "http://www.promostandards.org/WSDL/ProductDataService/2.0.0/SharedObjects/"
NS_PPC    = "http://www.promostandards.org/WSDL/PricingAndConfiguration/1.0.0/"
NS_PPC_SO = "http://www.promostandards.org/WSDL/PricingAndConfiguration/1.0.0/SharedObjects/"

# ET namespace map for XPath queries
_NS_PS  = {"ps": NS_PS,  "so": NS_PS_SO,  "s": "http://schemas.xmlsoap.org/soap/envelope/"}
_NS_PPC = {"ppc": NS_PPC, "so": NS_PPC_SO, "s": "http://schemas.xmlsoap.org/soap/envelope/"}


class PromoStandardsError(Exception):
    """Raised when the PS service returns an error code."""
    def __init__(self, code, description):
        self.code = code
        self.description = description
        super().__init__(f"PS error {code}: {description}")


def _soap_post(url: str, action: str, body: str, timeout: int = 30) -> ET.Element:
    """POST a SOAP request and return the parsed XML root element."""
    resp = requests.post(
        url,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{action}"',
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return ET.fromstring(resp.text)


def _check_ps_error(root: ET.Element) -> None:
    """Raise PromoStandardsError if the response contains a ServiceMessage with Error severity."""
    for msg in root.iter(f"{{{NS_PS_SO}}}ServiceMessage"):
        severity = msg.findtext(f"{{{NS_PS_SO}}}severity", "")
        if severity.lower() == "error":
            code = msg.findtext(f"{{{NS_PS_SO}}}code", "?")
            desc = msg.findtext(f"{{{NS_PS_SO}}}description", "")
            raise PromoStandardsError(code, desc)


def _check_ppc_error(root: ET.Element) -> None:
    """Raise PromoStandardsError if PPC response contains an error service message."""
    for msg in root.iter(f"{{{NS_PPC_SO}}}ServiceMessage"):
        severity = msg.findtext(f"{{{NS_PPC_SO}}}severity", "")
        if severity.lower() == "error":
            code = msg.findtext(f"{{{NS_PPC_SO}}}code", "?")
            desc = msg.findtext(f"{{{NS_PPC_SO}}}description", "")
            raise PromoStandardsError(code, desc)


class PromoStandardsClient:
    """
    Client for LogoIncluded's PromoStandards endpoints.

    Methods return plain dicts / lists — no Django model dependencies,
    so this module is safe to import anywhere (tests, scripts, management commands).
    """

    def __init__(self, username: str = PS_USERNAME, password: str = PS_PASSWORD):
        self.username = username
        self.password = password

    # ── ProductData ────────────────────────────────────────────────────────────

    def get_sellable_products(self, sellable: bool = True) -> list[dict]:
        """
        Call getProductSellable → list of {"productId": str, "partId": str} dicts.
        Returns every product/part combination currently marked as sellable.
        """
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ps="{NS_PS}"
                  xmlns:so="{NS_PS_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ps:GetProductSellableRequest>
      <so:wsVersion>2.0.0</so:wsVersion>
      <so:id>{self.username}</so:id>
      <so:password>{self.password}</so:password>
      <so:isSellable>{"true" if sellable else "false"}</so:isSellable>
    </ps:GetProductSellableRequest>
  </soapenv:Body>
</soapenv:Envelope>"""

        root = _soap_post(PRODUCT_DATA_URL, "getProductSellable", body)
        _check_ps_error(root)

        results = []
        for item in root.iter(f"{{{NS_PS}}}ProductSellable"):
            product_id = item.findtext(f"{{{NS_PS_SO}}}productId", "")
            part_id    = item.findtext(f"{{{NS_PS_SO}}}partId", "")
            if product_id:
                results.append({"productId": product_id, "partId": part_id})
        return results

    def get_product(self, product_id: str, localization_country: str = "US",
                    localization_language: str = "en") -> dict:
        """
        Call getProduct → dict with product details.

        Returns:
            {
                "productId": str,
                "productName": str,
                "description": str,
                "primaryImageUrl": str,
                "productBrand": str,
                "parts": [
                    {
                        "partId": str,
                        "description": str,
                        "primaryColor": str,
                        "countryOfOrigin": str,
                    }, ...
                ],
                "dimensions": {
                    "dimensionUom": str, "depth": str, "height": str,
                    "width": str, "weightUom": str, "weight": str,
                },
                "categories": [str, ...],
            }
        Raises PromoStandardsError on error responses.
        """
        # Field order per GetProductRequest.xsd:
        # wsVersion, id, password, localizationCountry, localizationLanguage, productId
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ps="{NS_PS}"
                  xmlns:so="{NS_PS_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ps:GetProductRequest>
      <so:wsVersion>2.0.0</so:wsVersion>
      <so:id>{self.username}</so:id>
      <so:password>{self.password}</so:password>
      <so:localizationCountry>{localization_country}</so:localizationCountry>
      <so:localizationLanguage>{localization_language}</so:localizationLanguage>
      <so:productId>{product_id}</so:productId>
    </ps:GetProductRequest>
  </soapenv:Body>
</soapenv:Envelope>"""

        root = _soap_post(PRODUCT_DATA_URL, "getProduct", body)
        _check_ps_error(root)

        SO = NS_PS_SO
        product_el = root.find(f".//{{{NS_PS}}}Product")
        if product_el is None:
            raise PromoStandardsError("NO_PRODUCT", f"No Product element in response for {product_id}")

        def so(tag):
            return product_el.findtext(f"{{{SO}}}{tag}", "")

        # Dimensions (on the product level, if present)
        dim_el = product_el.find(f"{{{NS_PS}}}Dimension")
        dimensions = {}
        if dim_el is not None:
            for field in ("dimensionUom", "depth", "height", "width", "weightUom", "weight"):
                dimensions[field] = dim_el.findtext(f"{{{SO}}}{field}", "")

        # Categories
        categories = []
        for cat_el in product_el.iter(f"{{{NS_PS}}}ProductCategory"):
            cat = cat_el.findtext("category", "")
            sub = cat_el.findtext("subCategory", "")
            categories.append(f"{cat}/{sub}" if sub else cat)

        # Parts
        parts = []
        for part_el in product_el.iter(f"{{{NS_PS}}}Part"):
            part = {
                "partId":         part_el.findtext(f"{{{SO}}}partId", ""),
                "description":    part_el.findtext(f"{{{SO}}}description", ""),
                "primaryColor":   "",
                "countryOfOrigin": part_el.findtext(f"{{{SO}}}countryOfOrigin", ""),
            }
            # primaryColor may be nested under PartColor or ColorArray
            color_el = part_el.find(f".//{{{SO}}}colorName")
            if color_el is not None and color_el.text:
                part["primaryColor"] = color_el.text
            parts.append(part)

        return {
            "productId":      so("productId"),
            "productName":    so("productName"),
            "description":    so("description"),
            "primaryImageUrl": so("primaryImageUrl"),
            "productBrand":   so("productBrand"),
            "parts":          parts,
            "dimensions":     dimensions,
            "categories":     categories,
        }

    def get_unique_product_ids(self) -> list[str]:
        """Return a deduplicated list of productIds from getProductSellable."""
        seen = []
        seen_set = set()
        for item in self.get_sellable_products():
            pid = item["productId"]
            if pid not in seen_set:
                seen_set.add(pid)
                seen.append(pid)
        return seen

    # ── PPC (Pricing & Configuration) ──────────────────────────────────────────

    def get_pricing(self, product_id: str, part_id: str = "",
                    currency: str = "USD", localization_country: str = "US",
                    localization_language: str = "en") -> dict:
        """
        Call getConfigurationAndPricing → dict with price breaks.

        Returns:
            {
                "productId": str,
                "parts": [
                    {
                        "partId": str,
                        "description": str,
                        "priceBreaks": [
                            {"minQty": int, "price": float, "uom": str}, ...
                        ],
                    }, ...
                ],
            }
        """
        part_el = f"<so:partId>{part_id}</so:partId>" if part_id else ""
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ppc="{NS_PPC}"
                  xmlns:so="{NS_PPC_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ppc:GetConfigurationAndPricingRequest>
      <so:wsVersion>1.0.0</so:wsVersion>
      <so:id>{self.username}</so:id>
      <so:password>{self.password}</so:password>
      <so:productId>{product_id}</so:productId>
      {part_el}
      <so:currency>{currency}</so:currency>
      <so:localizationCountry>{localization_country}</so:localizationCountry>
      <so:localizationLanguage>{localization_language}</so:localizationLanguage>
    </ppc:GetConfigurationAndPricingRequest>
  </soapenv:Body>
</soapenv:Envelope>"""

        root = _soap_post(PPC_URL, "getConfigurationAndPricing", body)
        _check_ppc_error(root)

        SO = NS_PPC_SO
        NS = NS_PPC

        parts = []
        for part_el in root.iter(f"{{{NS}}}Part"):
            price_breaks = []
            for pp in part_el.iter(f"{{{NS}}}PartPrice"):
                try:
                    price_breaks.append({
                        "minQty": int(pp.findtext("minQuantity", "0")),
                        "price":  float(pp.findtext("price", "0")),
                        "uom":    pp.findtext("priceUom", "EA"),
                    })
                except ValueError:
                    pass
            parts.append({
                "partId":      part_el.findtext(f"{{{SO}}}partId", ""),
                "description": part_el.findtext(f"{{{SO}}}partDescription", ""),
                "priceBreaks": price_breaks,
            })

        return {"productId": product_id, "parts": parts}

    def get_available_locations(self, product_id: str,
                                localization_country: str = "US",
                                localization_language: str = "en") -> list[dict]:
        """
        Call getAvailableLocations → list of {"locationId": str, "locationName": str} dicts.
        """
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ppc="{NS_PPC}"
                  xmlns:so="{NS_PPC_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ppc:GetAvailableLocationsRequest>
      <so:wsVersion>1.0.0</so:wsVersion>
      <so:id>{self.username}</so:id>
      <so:password>{self.password}</so:password>
      <so:productId>{product_id}</so:productId>
      <so:localizationCountry>{localization_country}</so:localizationCountry>
      <so:localizationLanguage>{localization_language}</so:localizationLanguage>
    </ppc:GetAvailableLocationsRequest>
  </soapenv:Body>
</soapenv:Envelope>"""

        root = _soap_post(PPC_URL, "getAvailableLocations", body)
        _check_ppc_error(root)

        results = []
        for loc in root.iter(f"{{{NS_PPC}}}AvailableLocation"):
            results.append({
                "locationId":   loc.findtext(f"{{{NS_PPC_SO}}}locationId", ""),
                "locationName": loc.findtext(f"{{{NS_PPC_SO}}}locationName", ""),
            })
        return results
