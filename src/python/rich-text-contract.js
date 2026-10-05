(()=>{'use strict';
const DATA={"version":1,"maxParagraphs":256,"maxRuns":2048,"maxEntities":256,"maxDocumentCharacters":100000,"maxParagraphCharacters":20000,"maxRunCharacters":10000,"maxTabStops":16,"maxListDepth":8,"maxHtmlBytes":200000,"maxIdLength":64,"maxStyleIdLength":64,"maxEntityTitleLength":160,"locales":["en","km","und"],"directions":["auto","ltr","rtl"],"alignments":["left","center","right","justify"],"listTypes":["none","bullet","ordered"],"listMarkers":["disc","circle","square","decimal","lower-alpha","upper-alpha","lower-roman","upper-roman"],"tabAlignments":["left","center","right","decimal"],"tabLeaders":["none","dots","dashes","line"],"urlProtocols":["https","http","mailto","tel"],"markKeys":["strong","emphasis","underline","strikethrough","colorToken","fontPairing","fontSize"],"paragraphOverrideKeys":["textAlign","lineHeight","spaceBefore","spaceAfter","indentLeft","indentRight","firstLineIndent","direction"],"maxLegacyNesting":32};
const freezeList=key=>Object.freeze([...(DATA[key]||[])]);
window.EInviteRichTextContract=Object.freeze({
 version:DATA.version,data:Object.freeze(DATA),
 MAX_PARAGRAPHS:DATA.maxParagraphs,MAX_RUNS:DATA.maxRuns,MAX_ENTITIES:DATA.maxEntities,
 MAX_DOCUMENT_CHARACTERS:DATA.maxDocumentCharacters,MAX_PARAGRAPH_CHARACTERS:DATA.maxParagraphCharacters,
 MAX_RUN_CHARACTERS:DATA.maxRunCharacters,MAX_TAB_STOPS:DATA.maxTabStops,MAX_LIST_DEPTH:DATA.maxListDepth,
 MAX_HTML_BYTES:DATA.maxHtmlBytes,MAX_LEGACY_NESTING:DATA.maxLegacyNesting,MAX_ID_LENGTH:DATA.maxIdLength,MAX_STYLE_ID_LENGTH:DATA.maxStyleIdLength,
 locales:freezeList('locales'),directions:freezeList('directions'),alignments:freezeList('alignments'),
 listTypes:freezeList('listTypes'),listMarkers:freezeList('listMarkers'),tabAlignments:freezeList('tabAlignments'),
 tabLeaders:freezeList('tabLeaders'),urlProtocols:freezeList('urlProtocols'),markKeys:freezeList('markKeys'),
 paragraphOverrideKeys:freezeList('paragraphOverrideKeys')
});
})();
