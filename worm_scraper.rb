require 'nokogiri'
require 'open-uri'
require 'uri'
require 'base64'
require 'pry'

@domain = 'https://meaningness.com'
def ensure_domain(url)
  if url.include? 'http'
    return url
  else
    return @domain + url
  end
end

@index_page = 'https://meaningness.com/'
doc = Nokogiri::HTML(open(@index_page))
@chapters = doc.css('.book-toc a').map { |a| a['href'] }
@chapters_disposable = @chapters.clone()
$stderr.puts "Chapters:", @chapters

@mode = :indexed # :indexed or :sequential
#set to first chapter
if @mode == :indexed
  @next_chapter = ensure_domain(@chapters_disposable.shift())
else
  @next_chapter = 'http://mindingourway.com/half-assing-it-with-everything-youve-got/'
end
# @next_chapter = 'https://sinceriously.fyi/false-faces/'
@toc = "<h1>Table of Contents</h1>"
@book_body = ""
@index = 1
@chapterLinkMap = {}

def convert_local_href(href_with_hash)
  if href_with_hash[0] == '#'
    return href_with_hash
  end
  href, hash_part = href_with_hash.split('#')
  if href.include? @domain
    without_domain = href.sub(@domain, '')
    with_domain = href
  else
    without_domain = href
    with_domain = @domain + href
  end
  if @chapters.include? without_domain
    localized = "#chap#{@chapters.index(without_domain)}"
  elsif @chapters.include? with_domain
    localized = "#chap#{@chapters.index(with_domain)}"
  end
  if localized
    if !hash_part.nil? and hash_part.length > 0
      return "#" + hash_part
    else
      return localized
    end
  end
  return href_with_hash
end

# $stderr.puts convert_local_href('/stances-toc')
# exit

while @next_chapter #and @index < 10
  #check if url is weird
  @next_chapter.sub!('https://', 'http://')
  if @next_chapter.to_s.include?("½")
    @next_chapter = URI.escape(@next_chapter)
  end
  doc = Nokogiri::HTML(open(@next_chapter))
  #get
  @chapter_title = doc.css('#page-title').first #html formatted

  #modify chapter to have link
  @chapter_title_plain = @chapter_title.content
  $stderr.puts @chapter_title_plain
  # puts doc
  @chapter_content = doc.css('#main-content').first #gsub first p
  #clean
  # @chapter_content.search('.//div').remove
  @chapter_content.search('.tweet').remove
  @chapter_content.search('nav .links').remove
  # @to_remove = doc.css('.post-content p').first #gsub first p
  @chapter_content = @chapter_content.to_s#.gsub(@to_remove.to_s,"")
  #write
  @book_body << "<h1 id=\"chap#{@index.to_s}\">#{@chapter_title_plain}</h1>"
  @book_body << @chapter_content
  chapter_anchor = "<a href=\"#chap#{@index.to_s}\">#{@chapter_title_plain}</a><br>"
  @toc << chapter_anchor
  @chapterLinkMap[@next_chapter] = "#chap#{@index.to_s}"
  @index += 1
  #next
  if @mode == :indexed
    @next_chapter = @chapters_disposable.shift()
  else
    @next_chapter = if doc.css('.right.navlink').last
                      doc.css('.right.navlink').last['href']
                    else
                      false
                    end
  end
  if @next_chapter
    @next_chapter = ensure_domain(@next_chapter)
  end
  # @next_chapter = false #nocommit
end

@book_body.scan(/<img.*?src="(.*?)".*?>/).each_with_index { |match, i|
  img_url = match[0]
  # File.open("./sinceriously/#{i}.png", 'wb') { |fo|
  #   fo.write(open(img_url).read)
  # }
  # @book_body.sub!(img_url, "#{i.to_s}.png")
  $stderr.puts "Image URL:", img_url, ensure_domain(img_url)
  full_img_url = ensure_domain(img_url)
  full_img_url = full_img_url.gsub(/%20$/, '')
  begin
    encoded = Base64.encode64(open(full_img_url).read)
    if full_img_url.include? '.svg'
      data_type = 'image/svg+xml;base64'
    else
      data_type = 'image/png;base64'
    end
    @book_body.gsub!(img_url, "data:#{data_type};base64,#{encoded}")
  rescue OpenURI::HTTPError
    $stderr.puts "ERROR: Unable to fetch URL #{full_img_url}"
  end
}

replaced_local_links = {}
invert_replaced_local_links = {}

total_result = @toc + @book_body

total_result.scan(/href="([^"]*?)"/).each_with_index { |match, i|
  href = match[0]
  # binding.pry
  local_href = convert_local_href(href)
  # $stderr.puts("#{local_href} in? #{replaced_local_links.to_s}")
  # $stderr.puts("#{local_href} in? #{invert_replaced_local_links.to_s}")
  if !invert_replaced_local_links[local_href].nil?
    next
  elsif !replaced_local_links[local_href].nil?
    local_href = replaced_local_links[local_href]
  elsif local_href.start_with?('#')
    uniqued_href = local_href + '_' +rand(10000000000).to_s
    total_result.gsub!("\"#{local_href}\"", "\"#{uniqued_href}\"")
    $stderr.puts "matching id=\"#{local_href[1,10000]}\" :" + (!total_result.match("id=\"#{local_href[1,10000]}\"").nil?).to_s
    total_result.gsub!("id=\"#{local_href[1,10000]}\"", "id='#{uniqued_href[1,10000]}'")
    replaced_local_links[local_href] = uniqued_href
    invert_replaced_local_links[uniqued_href] = local_href
    local_href = uniqued_href
    next
  end
  $stderr.puts "Local ref: '#{href}' -> '#{local_href}'"
  total_result.gsub!("\"#{href}\"", "\"#{local_href}\"")
}

$stderr.puts "Writing Book..."

puts total_result
