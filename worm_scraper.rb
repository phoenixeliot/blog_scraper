require 'nokogiri'
require 'open-uri'
require 'uri'
require 'base64'

#set to first chapter
@next_chapter = 'https://sinceriously.fyi/inconceivable/'
# @next_chapter = 'https://sinceriously.fyi/false-faces/'
@toc = "<h1>Table of Contents</h1>"
@book_body = ""
@index = 1

while @next_chapter
  #check if url is weird
  @next_chapter.sub!('http://', 'https://')
  if @next_chapter.to_s.include?("½")
    @next_chapter = URI.escape(@next_chapter)
  end
  doc = Nokogiri::HTML(open(@next_chapter))
  #get
  @chapter_title = doc.css('h1.entry-title').first #html formatted

  #modify chapter to have link
  @chapter_title_plain = @chapter_title.content
  $stderr.puts @chapter_title_plain
  @chapter_content = doc.css('div.entry-content').first #gsub first p
  #clean
  @chapter_content.search('.//div').remove
  @to_remove = doc.css('div.entry-content p').first #gsub first p
  @chapter_content = @chapter_content.to_s#.gsub(@to_remove.to_s,"")
  #write
  @book_body << "<h1 id=\"chap#{@index.to_s}\">#{@chapter_title_plain}</h1>"
  @book_body << @chapter_content
  @toc << "<a href=\"#chap#{@index.to_s}\">#{@chapter_title_plain}</a><br>"
  @index += 1
  #next
  @next_chapter = if doc.css('div.nav-next a').last&.content.to_s.include?("Next")
                    doc.css('div.nav-next a').last['href']
                  else
                    false
                  end
  # @next_chapter = false #nocommit
end

@book_body.scan(/<img.*?src="(.*?)".*?>/).each_with_index { |match, i|
  imgUrl = match[0]
  # File.open("./sinceriously/#{i}.png", 'wb') { |fo|
  #   fo.write(open(imgUrl).read)
  # }
  # @book_body.sub!(imgUrl, "#{i.to_s}.png")
  
  encoded = Base64.encode64(open(imgUrl).read)
  @book_body.sub!(imgUrl, "data:image/png;base64,#{encoded}")
}

$stderr.puts "Writing Book..."

puts @toc
puts @book_body
