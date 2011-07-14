#!/usr/bin/ruby
#
# Prereqs:
#
#   * svn checkout of foundation:voter and foundation:Meetings
#   * Web server with the ability to run cgi (Apache httpd recommended)
#   * Python 2.6.x
#   * Ruby 1.8.x
#   * Java 1.1 or later
#   * Vote-0-4.jar from the vote-0-4.zip found at:
#       http://sourceforge.net/projects/votesystem/files/votesystem/0.4/
#   * cgi-spa gem ([sudo] gem install cgi-spa)
#   * (optional) jQuery http://code.jquery.com/jquery.min.js
#
# Installation instructions:
#
#    ruby whatif.rb --install=/var/www
#
#    1) Specify a path that supports cgi, like public-html or Sites.
#    2) Modify the VOTER variable in the generated whatif.cgi to point to
#       your copy of Vote-0-4.jar
#    3) (optional, but recommended) download jquery.min.js into
#       your installation directory.
#
# Execution instructions:
#
#   Point your web browser at your cgi script.  For best results, use
#   Firefox 4 or a WebKit based browser, like Google Chrome.

MEETINGS  = File.expand_path('../Meetings') unless defined? MEETINGS
NSTV   = 'monitoring/nstv-rank.py'
FILTER = 'vote-filter.py'
VOTER  = '/home/rubys/tmp/Vote-0-4.jar' unless defined? VOTER

require 'rubygems'
require 'cgi-spa'
require 'tempfile'

date = $param.delete('date');
if date
  $raw_votes = "#{MEETINGS}/#{date}/raw_board_votes.txt"
else
  $raw_votes = Dir["#{MEETINGS}/*/raw_board_votes.txt"].sort.last
end

def ini(vote)
  vote.sub('/raw_','/').sub('votes.','nominations.').sub('.txt','.ini')
end

def filtered_election(seats, candidates)
  votes = Tempfile.new('votes')
  votes << `python #{NSTV} #{$raw_votes} |
            python #{FILTER} #{candidates.join(' ')}`
  votes.flush
  output = `java -cp  #{VOTER} VoteMain -system stv-meek \
            -seats #{seats} #{votes.path}`
  votes.unlink
  output.scan(/.*elected$/).inject(Hash.new('none')) do |results, line|
    name, status = line.scan(/^(.*?)\s+(n?o?t?\s?elected)$/).flatten
    results.merge({name[0..8].gsub(/\W/,'') => status.gsub(/\s/, '-')})
  end
end

# XMLHttpRequest (AJAX)
$cgi.json do
  filtered_election($param.delete('seats'), $param.keys)
end

# main output
$cgi.html do |x|
  x.header do
    x.title 'STV Explorer'
    x.style! <<-EOF
       body {background-color: #F9F7ED}
       h1 {font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}
       h1 {font-size: 2em; font-weight: normal}
       label {-webkit-transition: background-color 1s}
       label {-moz-transition: background-color 1s} /* firefox 4 */
       label {display: inline-block; min-width: 5em; font-size: x-large}
       label[for=seats] {display: inline; line-height: 250%}
       p, input[type=checkbox] {margin-left: 1em}
       .elected {background: #0F0}
       .not-elected {background: #F00}
       .none {background: yellow}
       select {display: block; margin: 0 0 1em 1em; font-size: 140%}
    EOF
    x.script '', :src =>'jquery.min.js'
    x.script! <<-EOF
      $(document).ready(function() {
        // submit form using XHR; update class for labels based on results
        var refresh = function() {
          $.getJSON('', $('#vote').serialize(), function(results) {
            for (var name in results) {
              $('#'+name).attr('class', results[name]);
            }
          });
          return false;
        }

        // On checkbox click, remove class from associated label & refresh
        $(':checkbox').click(function() {
          $('label[for='+$(this).attr('id')+']').attr('class', 'none');
          refresh();
        });

        // On checkbox click, remove class from associated label & refresh
        $('select').change(function() {
          $('input[value=submit]').attr('name', 'reset');
          $('input[value=submit]').click();
        });

        // If JS is enabled, we don't need a submit button
        $('input[type=submit]').hide();

        // Add up and down arrows and refresh on change
        var seats = $('#seats');
        seats.keyup(function() {return refresh()});
        seats.before($('<input type="submit" value="&#x21D3;"/>').click(
          function() {
            if (seats.val()>1) {seats.val(seats.val()-1);}
            return refresh();
          }
        ));
        seats.after($('<input type="submit" value="&#x21D1;"/>').click(
          function() {
            if (seats.val()<$(':checkbox').length) {seats.val(seats.val()-0+1);}
            return refresh();
          }
        ));
      });
    EOF
  end

  x.body do
    x.h1 'STV Explorer'
    
    $nominees = Hash[*File.read(ini($raw_votes)).scan(/^(\w):\s*(.*)/).flatten]

    if $HTTP_POST and not $param.delete('reset')
      # if JS is disabled or jQuery not found, fall back to simple forms.
      seats   = $param.delete('seats')
      $param.delete('submit')
      results = filtered_election(seats, $param.keys)
    else
      # Initial display
      seats   = '9'
      results = filtered_election(seats, $nominees.keys)
      $param.clear
    end

    # form of nominees and seats
    x.form :method => 'post', :id => 'vote' do
      x.select :name => 'date' do
        Dir["#{MEETINGS}/*/raw_board_votes.txt"].sort.reverse.each do |votes|
	  next unless File.exist? ini(votes)
	  date = votes[/(\d+)\/raw_board_votes.txt$/,1]
          display = date.sub(/(\d{4})(\d\d)(\d\d)/,'\1-\2-\3')
          attrs = {:value => date}
	  attrs[:selected] = 'selected' if votes == $raw_votes
          x.option display, attrs
	end
      end

      $nominees.sort_by {|letter, name| name}.each do |letter, name|
        attrs = {:type=>'checkbox', :name=>letter, :id=>letter}
        if $param.keys.empty? or not $param[letter].empty?
          attrs[:checked]='checked'
        end
        x.input attrs

        id = name[0..8].gsub(/\W/,'')
        x.label name, :id=>id, :for=>letter, :class=>results[id] 
        x.br
      end

      x.label 'seats:', :for=>'seats'
      x.input :name=>'seats', :id=>'seats', :value=>seats, :size=>1
      x.br

      x.input :type=>'submit', :value=>'submit', :name => 'submit'
    end

    x.p do
      x.a 'Background Info', :href=>'http://wiki.apache.org/general/BoardVoting'
    end
  end
end

__END__
VOTER = '/home/rubys/tmp/Vote-0-4.jar'
