"""
PromoStandards API — LogoIncluded
Confirmed working namespace pattern (discovered via XSD inspection + live testing):

  - Wrapper element:  explicit prefix in MAIN namespace (e.g. ps:GetProductSellableRequest)
  - Child elements:   explicit prefix in SHARED OBJECTS namespace (e.g. so:wsVersion)
  - Both namespaces declared at Envelope level

XSD schema source:
  https://productdata.logoincluded.com/wsdl/GetProductSellableRequest.xsd
  → child fields use ref="ns3:wsVersion" where ns3 = SharedObjects namespace

ENDPOINTS (from PromoStandards public directory):
  ProductData:  https://productdata.logoincluded.com/ProductData.svc
  MediaContent: https://mediacontent.logoincluded.com/MediaContent.svc  ← broken server-side (always 115)
  PPC:          https://productprice.logoincluded.com/ProductPrice.svc

NOTE: Run this script on a machine with direct internet access (e.g. Railway).
      The local dev sandbox proxy blocks these endpoints.

Run: python promostandards_test.py
"""

import requests

USERNAME = "alexkharrod@gmail.com"
PASSWORD = "REDACTED"

PRODUCT_DATA_URL  = "https://productdata.logoincluded.com/ProductData.svc"
MEDIA_CONTENT_URL = "https://mediacontent.logoincluded.com/MediaContent.svc"
PPC_URL           = "https://productprice.logoincluded.com/ProductPrice.svc"

# Main service namespaces
NS_PS  = "http://www.promostandards.org/WSDL/ProductDataService/2.0.0/"
NS_MC  = "http://www.promostandards.org/WSDL/MediaService/1.0.0/"
NS_PPC = "http://www.promostandards.org/WSDL/PricingAndConfiguration/1.0.0/"

# SharedObjects namespaces — child elements (wsVersion, id, password, etc.) live here
# Confirmed from XSD: all child fields use ref="ns3:fieldName" → SharedObjects namespace
NS_PS_SO  = "http://www.promostandards.org/WSDL/ProductDataService/2.0.0/SharedObjects/"
NS_MC_SO  = "http://www.promostandards.org/WSDL/MediaService/1.0.0/SharedObjects/"
NS_PPC_SO = "http://www.promostandards.org/WSDL/PricingAndConfiguration/1.0.0/SharedObjects/"


def show(label, r):
    print(f"\n{'='*60}")
    print(f"{label}  [{r.status_code}]  len={len(r.text)}")
    if r.text.strip():
        print(r.text[:5000])
    else:
        print("(empty body)")


def soap(label, url, action, body):
    r = requests.post(url, data=body.encode("utf-8"), headers={
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"{action}"',
    }, timeout=30)
    show(label, r)
    return r


# ── ProductData: getProductSellable ───────────────────────────────────────────
# Returns list of all sellable productId+partId pairs.
# ✅ CONFIRMED WORKING — returns ~88KB of product data
soap("PS getProductSellable", PRODUCT_DATA_URL, "getProductSellable", f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ps="{NS_PS}"
                  xmlns:so="{NS_PS_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ps:GetProductSellableRequest>
      <so:wsVersion>2.0.0</so:wsVersion>
      <so:id>{USERNAME}</so:id>
      <so:password>{PASSWORD}</so:password>
      <so:isSellable>true</so:isSellable>
    </ps:GetProductSellableRequest>
  </soapenv:Body>
</soapenv:Envelope>""")


# ── ProductData: getProduct ───────────────────────────────────────────────────
# Returns full product detail for one product.
# Field order per XSD: wsVersion, id, password, localizationCountry, localizationLanguage, productId
# NOTE: no currencyCode field exists in PS 2.0.0 schema.
# ✅ CONFIRMED WORKING — tested with EC18 (returns name, description, parts, pricing, etc.)
soap("PS getProduct EC18", PRODUCT_DATA_URL, "getProduct", f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ps="{NS_PS}"
                  xmlns:so="{NS_PS_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ps:GetProductRequest>
      <so:wsVersion>2.0.0</so:wsVersion>
      <so:id>{USERNAME}</so:id>
      <so:password>{PASSWORD}</so:password>
      <so:localizationCountry>US</so:localizationCountry>
      <so:localizationLanguage>en</so:localizationLanguage>
      <so:productId>EC18</so:productId>
    </ps:GetProductRequest>
  </soapenv:Body>
</soapenv:Envelope>""")


# ── MediaContent: getMediaContent ─────────────────────────────────────────────
# ❌ SERVER-SIDE ISSUE — always returns error 115 "wsVersion not found" regardless
#    of request format. Tested: all namespace variants, empty body, different versions.
#    This appears to be a misconfiguration on LogoIncluded's MC endpoint.
#    Left here for documentation; may start working if LogoIncluded fixes their service.
soap("MC getMediaContent EC18 (expect error 115 — server-side issue)", MEDIA_CONTENT_URL, "getMediaContent", f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:mc="{NS_MC}"
                  xmlns:so="{NS_MC_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <mc:GetMediaContentRequest>
      <so:wsVersion>1.0.0</so:wsVersion>
      <so:id>{USERNAME}</so:id>
      <so:password>{PASSWORD}</so:password>
      <so:mediaType>Image</so:mediaType>
      <so:productId>EC18</so:productId>
    </mc:GetMediaContentRequest>
  </soapenv:Body>
</soapenv:Envelope>""")


# ── PPC: getAvailableLocations ────────────────────────────────────────────────
# Returns imprint location IDs/names for a product.
# ✅ CONFIRMED WORKING — EC18 returns: locationId=1, locationName=front
soap("PPC getAvailableLocations EC18", PPC_URL, "getAvailableLocations", f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ppc="{NS_PPC}"
                  xmlns:so="{NS_PPC_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ppc:GetAvailableLocationsRequest>
      <so:wsVersion>1.0.0</so:wsVersion>
      <so:id>{USERNAME}</so:id>
      <so:password>{PASSWORD}</so:password>
      <so:productId>EC18</so:productId>
      <so:localizationCountry>US</so:localizationCountry>
      <so:localizationLanguage>en</so:localizationLanguage>
    </ppc:GetAvailableLocationsRequest>
  </soapenv:Body>
</soapenv:Envelope>""")


# ── PPC: getConfigurationAndPricing ──────────────────────────────────────────
# Returns price breaks and decoration config for a specific part.
# ✅ CONFIRMED WORKING — EC18_Black: 250+ @ $4.62, 500+ @ $4.16, etc.
soap("PPC getConfigurationAndPricing EC18_Black", PPC_URL, "getConfigurationAndPricing", f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ppc="{NS_PPC}"
                  xmlns:so="{NS_PPC_SO}">
  <soapenv:Header/>
  <soapenv:Body>
    <ppc:GetConfigurationAndPricingRequest>
      <so:wsVersion>1.0.0</so:wsVersion>
      <so:id>{USERNAME}</so:id>
      <so:password>{PASSWORD}</so:password>
      <so:productId>EC18</so:productId>
      <so:partId>EC18_Black</so:partId>
      <so:currency>USD</so:currency>
      <so:localizationCountry>US</so:localizationCountry>
      <so:localizationLanguage>en</so:localizationLanguage>
    </ppc:GetConfigurationAndPricingRequest>
  </soapenv:Body>
</soapenv:Envelope>""")
