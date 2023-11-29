Architecture notes for a componentized rewrite:

Behaviors to account for:
- Post-finding modes
  - Incremental (click 'next')
  - TOC
  - Expandy JS archive buttons
  - Wordpress paged multi-post history (eg https://www.aramjetbreaksthorns.com/2019/page/5/)
- Extra: Including linked same-domain posts that aren't in the TOC
- Generating TOC HTML from posts (option)
- Extract post content from scraped page
- Scraping and embedding images
- Post-rewriting plugin modules
  - Including blacklisting selectors
- TOC-rewriting plugin modules
- Modifying the HTML to include ↗︎︎ icons for external links
- Epub generation
  - Replacing page links with internal ebook links based on previous scraped info
- (others?)


Architectural thoughts
(meta: what well-established methods are there for diagraming this?)

PostIterator type
  - Takes parameters (toc location, starting post, etc)
  - Generates an ordered list of pages and their scraped HTML
    - (Have to include scraping it for at least the incremental version)
    - (Could I have something else scrape the pages' HTML and provide it to this in a back-and-forth?)
  - Can provide a list of all of the posts in addition to iterating, for the TOC

Transforms that need to happen:
- config -> selection of transforms to apply (and order?$$)
- page URL -> page HTML + redirect metadata
- TOC options+HTML -> list of pages + index metadata
- page HTML -> next page in sequential order + index metadata
- page HTML -> list of linked internal pages + index metadata
- page HTML -> list of linked external pages
- (list of internal URLs -> some kind of information about internal link redirects)
- all page&TOC HTML + URLs of pages -> pages&TOC HTML with links replaced for epub internal links
  - must also account for information about redirects (eg if page A links to page B, and that URL directs to page B', then the changed link should point to B' content in the ebook)


TODO for whately academy
- rename whateley_academy_original_timeline/shower_diagram_P4.jpg to whateley_academy_original_timeline/shower_diagram_P4.webp
- rename Josh_No_Weeny_P4.jpg to Josh_No_Weeny_P4.webp
- rename JoshHotdog_P4.jpg to JoshHotdog_P4.webp
- generally: find some way to detect the true image type of a file and use that for conversion instead of assuming based on its file extension, since some websites are just lying about it :|
