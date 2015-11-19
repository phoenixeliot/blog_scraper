require 'byebug'

text = File.read("worm.html")

rules = {
  /-“/ => '-”',
  "<em>“</em>" => '“',
  /([^\d\w])-([^\d\w])/ => '\1&mdash;\2',
  /“<\/p>/ => '”</p>',
  /([a-zA-Z\d’“”])-([^a-zA-Z\d])/ => '\1&mdash;\2',
  /“-/ => '“&mdash;',
  /<p>-/ => '<p>&mdash;',
  / -/ => ' &mdash;',
  /- / => '&mdash; ',
  /(\D)–(\D)/ => '\1&mdash;\2', # replace n-dashes with m-dashes
  "\u00A0 " => ' ',
  "\u00A0" => ' ',
  "  " => ' ',
  / (<[\/][a-zA-Z]+>)/ => '\1 ',
  / , / => ', ',
  /<a.*(Next|Last) Chapter<\/a>/ => "",
  /She’l([^l])/ => 'She’ll\1',
  /intp/ => "into",
  "replying old memories" => "replaying old memories",
  "Be nice to" => "It'd be nice to",
  "come little alive" => "come a little alive",
  "level-A" => "class-A",
  " he encouragement" => " the encouragement",
  "He was already out of her" => "He was already out of his",
  "Swimging" => "Swinging",
  "an negative" => "a negative",
  "The C.U.l" => "The C.U.I.",
  "the C.U. I" => "the C.U.I. I",
  "C.U.I.." => "C.U.I.",
  "Faulltine" => "Faultline",
  "Matroyshka" => "Matryoshka",
  "phone</p>" => "phone.</p>", 
  /<br>\n?-c/ => "<br>&ndash;c",
  "thirty-twenty five" => "thirty to twenty-five",
  /”Listen/ => '“Listen',
  /I[“”"]m/ => "I’m",
  /I[“”"]ll/ => "I’ll",
  "voice, I think" => "voice, “I think",
  
  # these ones are a little dangerous;
  # don't rearrange their order
  / ”<\/p>/ => '”</p>',
  /“Yes, dear. ”/ => "“Yes, dear.”",
  /(.{0,20}) ” ?(.{0,20})/ => '\1 “\2',
  /(”[^“”]+)Not exactly.”/ => '\1“Not exactly.”',
  '” Either of you?”' => ' Either of you?”',
  /” I said. ([A-Z][^“”]+”)/ => '” I said. “\1',
  /”([^“”<]+)”/ => '“\1”', # especially this one
  
  /”Noelle, “/ => '“Noelle,”',
  /“([^“”<]+) (he gasped)+/ => '“\1” \2',
  /fighting, “T/ => 'fighting,” T',
  /“([^“”<]+)“/ => '“\1”', # especially this one
      
  # works in progress (don't leave these in as-is)
}

rules.each do |key, value|
  puts "replacing #{key.inspect} with #{value.inspect}... "
  count = 0
  text.gsub(key) do |match|
    count += 1
    last_match = Regexp.last_match
    # debugger
    value2 = value.gsub("\\1", last_match[1] || "").gsub("\\2", last_match[2] || "")
    if(count < 10)
      puts "«#{match}» => «#{value2}»"
    end
    value2
  end
  text.gsub!(key, value)
  puts "#{count} replaced"
  puts
end

f = File.new("worm_edited.html", "w")
f.write(text)
f.close
