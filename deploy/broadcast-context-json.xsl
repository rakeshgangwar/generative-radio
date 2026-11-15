<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <!-- Reuse the JSON escaping supplied by the installed Icecast package. -->
  <xsl:import href="xml2json.xslt"/>
  <xsl:output method="text" encoding="UTF-8" media-type="application/json" omit-xml-declaration="yes"/>
  <xsl:template match="/">
    <xsl:variable name="source" select="/icestats/source[@mount='/radio.mp3'][1]"/>
    <xsl:variable name="title" select="substring(string($source/title),1,160)"/>
    <xsl:text>{"version":1,"available":</xsl:text>
    <xsl:choose>
      <xsl:when test="$source and string-length(normalize-space($title)) &gt; 0">
        <xsl:text>true,"title":</xsl:text>
        <xsl:call-template name="escape-string"><xsl:with-param name="s" select="$title"/></xsl:call-template>
      </xsl:when>
      <xsl:otherwise><xsl:text>false,"title":""</xsl:text></xsl:otherwise>
    </xsl:choose>
    <xsl:text>}</xsl:text>
  </xsl:template>
</xsl:stylesheet>
