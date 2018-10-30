require 'nokogiri'
require 'open-uri'
require 'uri'
require 'base64'

@domain = 'http://mindingourway.com'
def ensure_domain(url)
  if url.include? 'http'
    return url
  else
    return @domain + url
  end
end

@index_page = 'http://mindingourway.com/guilt/'
doc = Nokogiri::HTML(open(@index_page))
@chapters = doc.css('.post-content a').map { |a| a['href'] }
$stderr.puts @chapters

@mode = :indexed # :indexed or :sequential
#set to first chapter
if @mode == :indexed
  @next_chapter = ensure_domain(@chapters.shift())
else
  @next_chapter = 'http://mindingourway.com/half-assing-it-with-everything-youve-got/'
end
# @next_chapter = 'https://sinceriously.fyi/false-faces/'
@toc = "<h1>Table of Contents</h1>"
@book_body = ""
@index = 1

while @next_chapter
  #check if url is weird
  @next_chapter.sub!('https://', 'http://')
  if @next_chapter.to_s.include?("½")
    @next_chapter = URI.escape(@next_chapter)
  end
  doc = Nokogiri::HTML(open(@next_chapter))
  #get
  @chapter_title = doc.css('.post-title').first #html formatted

  #modify chapter to have link
  @chapter_title_plain = @chapter_title.content
  $stderr.puts @chapter_title_plain
  # puts doc
  @chapter_content = doc.css('.post-content').first #gsub first p
  #clean
  @chapter_content.search('.//div').remove
  # @to_remove = doc.css('.post-content p').first #gsub first p
  @chapter_content = @chapter_content.to_s#.gsub(@to_remove.to_s,"")
  #write
  @book_body << "<h1 id=\"chap#{@index.to_s}\">#{@chapter_title_plain}</h1>"
  @book_body << @chapter_content
  @toc << "<a href=\"#chap#{@index.to_s}\">#{@chapter_title_plain}</a><br>"
  @index += 1
  #next
  if @mode == :indexed
    @next_chapter = @chapters.shift()
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
  encoded = Base64.encode64(open(full_img_url).read)
  @book_body.gsub!(img_url, "data:image/png;base64,#{encoded}")
}

$stderr.puts "Writing Book..."

puts @toc
puts @book_body
