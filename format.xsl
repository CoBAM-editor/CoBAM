<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet  version="2.0"  
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"  
				xmlns:tei="http://www.tei-c.org/ns/1.0"
                  xmlns:saxon="http://icl.com/saxon"
                extension-element-prefixes="saxon">

<xsl:output method="html" 
            encoding="UTF-8"
            indent="yes" 
			doctype-public="-//W3C//DTD HTML 4.01//EN" 
			omit-xml-declaration="yes"
            saxon:character-representation="native;decimal" />

<xsl:template match="/">
  <html>
  <head>
   <title>
       <xsl:value-of select="tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title" />
   </title>
   <link rel="stylesheet" type="text/css" href="format-html.css" />
   <link rel="stylesheet" type="text/css" href="format-html1.css" />
   <script src="script.js" type="text/javascript">
    <xsl:text disable-output-escaping="yes">&#32;</xsl:text>
   </script>
   <xsl:apply-templates select="tei:TEI/tei:teiHeader/tei:tagsDecl" />   
  </head>
  <body> <!--class="{substring-after(/tei:TEI/tei:text/@rendition,'#')}"-->
   <div id="facscont">
	<div id="facszone" />
	<img id="facs" title="" alt="facsimile image" />
   </div>
   <xsl:apply-templates select="//tei:listWit" mode="text" />
   <xsl:apply-templates />
   <xsl:apply-templates select="//tei:app" mode="beforeparagraph"/>
  </body>
 </html>
</xsl:template>

<xsl:template match="tei:teiHeader">
</xsl:template>

<xsl:template match="tei:listWit" mode="text">
 <div class="witList">
  <table>
   <xsl:apply-templates />
  </table>
 </div>
</xsl:template>

<xsl:template match="tei:listWit/tei:witness">
 <tr class="witness">
  <td class="mss">
   <xsl:apply-templates />
   <xsl:text> : </xsl:text>
  </td>
  <td class="sigil">
   <xsl:value-of select="substring-after(@xml:id,'M')" />
  </td>
 </tr>
</xsl:template>

<xsl:template match="tei:listWit/tei:witness" mode="app">
   <xsl:choose>
     <xsl:when test="tei:abbr">
		<xsl:apply-templates select="tei:abbr" />
 	 </xsl:when>
 	 <xsl:otherwise>
       <xsl:apply-templates />
	 </xsl:otherwise>
   </xsl:choose>
</xsl:template>

<xsl:template match="tei:witness/tei:hi">
 <span style="{tei:rend}">
  <xsl:apply-templates />
 </span>
</xsl:template>

<xsl:template match="tei:rdg//tei:p">
 <xsl:text disable-output-escaping="yes">&#32; </xsl:text> 
 <xsl:apply-templates />
</xsl:template>

<xsl:template match="tei:note[@place='right' or @place='left']//p">
 <xsl:apply-templates />
</xsl:template>

<xsl:template match="tei:p">
 <p>
   <xsl:if test="@rendition">
     <!--xsl:attribute name="class">
       <xsl:value-of select="substring-after(@rendition,'#')" />
     </xsl:attribute-->
   </xsl:if>
   <xsl:if test="@rend">
     <xsl:attribute name="style">
       <xsl:value-of select="@rend" />
     </xsl:attribute>
   </xsl:if>
   <xsl:choose>
     <xsl:when test="parent::tei:hi">
	   <span style="{../@rend}">
         <xsl:apply-templates />
	   </span>
 	 </xsl:when>
 	 <xsl:otherwise>
       <xsl:apply-templates />
	 </xsl:otherwise>
   </xsl:choose>
 </p>
</xsl:template>

<xsl:template match="tei:head">
	<xsl:choose>
		<xsl:when test="@rendition='#rp-Heading_1'">
			<h1 class="{substring-after(@rendition,'#')}">
				<xsl:apply-templates />
			</h1>
		</xsl:when>
		<xsl:when test="@rendition='#rp-Heading_2'">
			<h2 class="{substring-after(@rendition,'#')}">
				<xsl:apply-templates />
			</h2>
		</xsl:when>
		<xsl:when test="@rendition='#rp-Heading_3'">
			<h3 class="{substring-after(@rendition,'#')}">
				<xsl:apply-templates />
			</h3>
		</xsl:when>
		<xsl:otherwise>
			<h4 class="{substring-after(@rendition,'#')}">
				<xsl:apply-templates />
			</h4>
		</xsl:otherwise>
	</xsl:choose>
</xsl:template>

<xsl:template match="tei:app" mode="beforeparagraph">
 <div class="app">
  <xsl:attribute name="id">
   <xsl:text>A</xsl:text>
   <xsl:number count="//tei:app" level="any" />
  </xsl:attribute>
    <span class="app2">
	  <xsl:apply-templates />
    </span>
 </div>
</xsl:template>

<xsl:template match="tei:app">
 <xsl:text disable-output-escaping="yes">&#32; </xsl:text> 
 <xsl:variable name="id">
  <xsl:number count="//tei:app" level="any" />
 </xsl:variable>
 <xsl:variable name="params">
  <xsl:text>('</xsl:text>
  <xsl:value-of select="$id" />
  <xsl:text>','</xsl:text>
  <xsl:value-of select="substring-after(@to,'#')" />
  <xsl:text>')</xsl:text>
 </xsl:variable>
 <!--xsl:if test="../../tei:body">
  <xsl:text disable-output-escaping="yes">&lt;p&gt;</xsl:text>
 </xsl:if-->
 <span class="appref" id="{$id}">
	 <xsl:attribute name="onmouseover">
	  <xsl:text>appref_mouseover</xsl:text>
	  <xsl:value-of select="$params" />
	 </xsl:attribute>
	 <xsl:attribute name="onmouseout">
	  <xsl:text>appref_mouseout</xsl:text>
	  <xsl:value-of select="$params" />
	 </xsl:attribute>
	 <xsl:attribute name="onclick">
	  <xsl:text>appref_click</xsl:text>
	  <xsl:value-of select="$params" />
	 </xsl:attribute>
	 <xsl:choose>
	  <xsl:when test="tei:rdg/tei:witStart">
	   <xsl:text> ▐► </xsl:text>
	  </xsl:when>
	  <xsl:when test="tei:rdg/tei:witEnd">
	   <xsl:text> ◄▌ </xsl:text>
	  </xsl:when>
	  <xsl:otherwise>
	   <xsl:text>&#xb0;</xsl:text>
	  </xsl:otherwise>
	 </xsl:choose> 
 </span>
 <!--xsl:if test="../../tei:body">
  <xsl:text disable-output-escaping="yes">&lt;/p&gt;</xsl:text>
 </xsl:if-->
 </xsl:template>

<xsl:template match="tei:anchor">
 <a id="{@xml:id}" class="anchor">
  <xsl:text>]</xsl:text>
 </a>
</xsl:template>

<xsl:template match="tei:rdg">
  <xsl:call-template name="Witnesses">
   <xsl:with-param name="mss" select="@wit" />
   <xsl:with-param name="det" select="@xml:id" />
  </xsl:call-template>
  <xsl:text disable-output-escaping="no">&#160;: </xsl:text>
  <xsl:choose>
   <xsl:when test="tei:witStart or tei:witEnd">
    <xsl:apply-templates />
   </xsl:when>
   <xsl:when test="normalize-space(string(current()))=''">
    <span style="font-style:italic;">
     <xsl:text> om. </xsl:text>
    </span>
   </xsl:when>
   <xsl:otherwise> 
    <xsl:apply-templates />
   </xsl:otherwise> 
  </xsl:choose>
  <xsl:if test="following-sibling::tei:rdg[position()=1]">
   <br />
  </xsl:if> 
</xsl:template>

<xsl:template name="Witnesses">
 <xsl:param name="mss" />
 <xsl:param name="det" />
 <span class="mss">
  <xsl:call-template name="AWitness">
   <xsl:with-param name="mss" select="concat(normalize-space($mss),' ')" />
   <xsl:with-param name="det" select="$det" />
  </xsl:call-template>
 </span>
</xsl:template>

<xsl:template name="AWitness">
 <xsl:param name="mss" />
 <xsl:param name="det" />
 <xsl:variable name="ms" select="substring-after(normalize-space(substring-before($mss,' ')),'#')" />
 <xsl:if test="$ms!=''">
  <xsl:choose>
   <xsl:when test="//tei:listWit/tei:witness[@xml:id=$ms]">
    <xsl:apply-templates select="//tei:listWit/tei:witness[@xml:id=$ms]" mode="app" />
   </xsl:when>
   <xsl:otherwise>
    <xsl:value-of select="$ms" />
   </xsl:otherwise>
  </xsl:choose>
  <xsl:if test="$det!=''">
   <xsl:for-each select="../tei:witDetail[@target=$det]">
    <xsl:if test="substring-after(@wit,'#')=$ms">
     <xsl:text> (</xsl:text>    
     <xsl:apply-templates />
     <xsl:text>)</xsl:text>
    </xsl:if>
   </xsl:for-each>
  </xsl:if>
 </xsl:if>
 <xsl:variable name="mss1" select="normalize-space(substring-after($mss,' '))" />
 <xsl:if test="$mss1!=''">
  <xsl:text> </xsl:text>
  <xsl:call-template name="AWitness">
   <xsl:with-param name="mss" select="concat($mss1,' ')" />
  </xsl:call-template>
 </xsl:if>
</xsl:template>

<xsl:template match="tei:witDetail">
</xsl:template>

<xsl:template match="tei:witStart">
 <i>
  <xsl:text> inc. </xsl:text>
 </i>
</xsl:template>

<xsl:template match="tei:witEnd">
 <i>
  <xsl:text> des. </xsl:text>
 </i>
</xsl:template>

<xsl:template match="tei:rdg/tei:note">
  <span class="rdg_note">
  <xsl:text> (</xsl:text> 
  <xsl:apply-templates />
  <xsl:text>) </xsl:text> 
  </span>
</xsl:template>

<xsl:template match="tei:note[@place='right' or @place='left']">
  <span class="{@place}">
  <xsl:apply-templates />
  </span>
</xsl:template>

<xsl:template match="tei:note[@place='foot']">
   <xsl:choose>
     <xsl:when test="@type='n3'"> <!-- assumes that Notes 3 containts only graphic links -->
		<xsl:apply-templates select="tei:milestone[@unit='facs']"/>
 	 </xsl:when>
 	 <xsl:otherwise>
		<span class="{@type}">
		<xsl:apply-templates />
		</span>
	</xsl:otherwise>
   </xsl:choose>	
</xsl:template>

<xsl:template match="tei:anchor[@type='sync']">
	<a class="sync">
		<xsl:attribute name="name">
			<xsl:text>s</xsl:text>
			<xsl:number count="anchor[@type='sync']" format="1" level="any" />
		</xsl:attribute>
	</a>
</xsl:template>

<xsl:template match="tei:anchor[@type='sync1']">
	<a class="sync">
		<xsl:attribute name="name">
			<xsl:text>s</xsl:text>
			<xsl:number count="anchor[@type='sync1']" format="1" level="any" />
			<xsl:text>.0</xsl:text>
		</xsl:attribute>
	</a>
</xsl:template>

<xsl:template match="tei:anchor[@type='sync2']">
	<a class="sync">
		<xsl:attribute name="name">
			<xsl:text>s</xsl:text>
			<xsl:number count="anchor[@type='sync1']" format="1" level="any" />
			<xsl:text>.</xsl:text>
			<xsl:number count="anchor[@type='sync2']" format="1" from="anchor[@type='sync1']" level="any" />
		</xsl:attribute>
	</a>
</xsl:template>

<xsl:template match="tei:emph">
 <span class="emph" name="{@n}">
   <xsl:apply-templates />
 </span>
</xsl:template>

<xsl:template match="tei:mentioned">
 <span class="mentioned">
   <xsl:apply-templates />
 </span>
</xsl:template>

<xsl:template match="tei:mentioned//hi[@rend='b']">
</xsl:template>

<xsl:template match="tei:zone" mode="ref">
	<span class="facslink" name="{concat('zl',@xml:id)}" > 
		<xsl:attribute name="onmouseover">
			<xsl:text>showZone('</xsl:text> 
			<xsl:value-of select="../tei:graphic/@url" />
			<xsl:text>','</xsl:text> 
			<xsl:value-of select="@points" />
			<xsl:text>')</xsl:text>
		</xsl:attribute>
		<xsl:text>►</xsl:text> 
	</span>
</xsl:template>

<xsl:template match="tei:facsimile">
	<xsl:apply-templates select="tei:surface" />
</xsl:template>

<xsl:template match="tei:surface">
	<map name="{concat(tei:graphic/@url,'+map')}">
		<xsl:apply-templates select="tei:zone" />
	</map>
</xsl:template>

<xsl:template match="tei:zone">
 <area shape="poly" coords="{translate(@points,' ',',')}" href="javascript:findZoneTarget('{@xml:id}')" alt="" title="" />
</xsl:template>

<xsl:template match="tei:note[@type='n3']/tei:milestone[@unit='facs']">
	<xsl:variable name="fac" select="@facs" />
	<xsl:apply-templates select="//tei:facsimile/tei:surface/tei:zone[@xml:id=$fac]" mode="ref" />
</xsl:template>

<xsl:template match="tei:milestone">
  <xsl:choose>
   <xsl:when test="@unit='facs'">
	 <xsl:variable name="fac" select="@facs" />
	 <xsl:apply-templates select="//tei:facsimile/tei:surface/tei:zone[@xml:id=$fac]" mode="ref" />
   </xsl:when>
   <xsl:otherwise>
	  <span class="milestone-{@unit}">
		<xsl:value-of select="@n" />
		<xsl:apply-templates />
		</span>
   </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="tei:hi">
 <span style="{@rend}">
   <xsl:apply-templates />
 </span>
</xsl:template>

<xsl:template match="tei:graphic">
	<img src="{@url}" style="width:{@width}; height:{@height}" />
</xsl:template>

<xsl:template match="tei:ref">
	<a href="{@target}" target="_blank">
		<xsl:apply-templates />
	</a>
</xsl:template>

<xsl:template match="tei:binaryObject">
	<img src="data:{@mimeType};base64,{current()}" style="width:{@width};height:{@height};{@rend}"/>
</xsl:template>

<xsl:template match="tei:tagsDecl">
	<style type="text/css">
		<xsl:apply-templates />
	</style>
</xsl:template>

<xsl:template match="tei:tagsDecl/tei:rendition[@scheme='css']">
	<xsl:text>.</xsl:text> 
	<xsl:value-of select="@xml:id" />
	<xsl:text> { </xsl:text> 
	<xsl:value-of select="." />
  	<xsl:text> } </xsl:text> 
    <xsl:text disable-output-escaping="yes">&#13; </xsl:text> 
</xsl:template>

</xsl:stylesheet>

