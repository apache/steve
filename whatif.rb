#!/usr/bin/ruby
#
# Prereqs:
#
#   * svn checkout of foundation:voter and foundation:Meetings
#   * Web server with the ability to run cgi (Apache httpd recommended)
#   * Python 2.6.x
#   * Ruby 1.8.x
#   * Java 1.1 or later
#   * Vote-0-4.jar from http://www.vdig.com/stv/download.html
#   * cgi-spa gem ([sudo] gem install cgi-spa)
#   * (optional) jQuery http://code.jquery.com/jquery-1.4.2.min.js
#
# Installation instructions:
#
#    ruby whatif.rb --install=/var/www
#
#    1) Specify a path that supports cgi, like public-html or Sites.
#    2) Modify the VOTER variable in the generated whatif.cgi to point to
#       your copy of Vote-0-4.jar
#    3) (optional, but recommended) download jquery-1.4.2.min.js into
#       your installation directory.
#
# Execution instructions:
#
#   Point your web browser at your cgi script.  For best results, use a
#   WebKit based browser, like Google Chrome.

VOTES  = '../Meetings/20100713/raw_board_votes.txt' unless defined? VOTES
NSTV   = 'monitoring/nstv-rank.py'
FILTER = 'vote-filter.py'
VOTER  = '/home/rubys/tmp/Vote-0-4.jar' unless defined? VOTER

NOMINEES = open(NSTV).read[/nominees = \{(.*?)\}/m,1].scan(/'(\w)':\s+'(.*?)'/)

def filtered_election(seats, candidates)
  votes = Tempfile.new('votes')
  votes << `python #{NSTV} #{VOTES} |
            python #{FILTER} #{candidates.join(' ')}`
  votes.flush
  output = `java -cp  #{VOTER} VoteMain -system stv-meek \
            -seats #{seats} #{votes.path}`
  votes.unlink
  output.scan(/.*elected$/).inject(Hash.new('none')) do |results, line|
    name, status = line.split(/\s+/,2)
    results.merge({name => status.gsub(/\s/, '-')})
  end
end

require 'rubygems'
require 'cgi-spa'
require 'tempfile'

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
    EOF
    x.script '', :src =>'/workbench/jquery-1.2.6.min.js'
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

        // If JS is enabled, we don't need a submit button
        $('input[type=submit]').remove();

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

    if $HTTP_POST
      # if JS is disabled or jQuery not found, fall back to simple forms.
      seats   = $param.delete('seats')
      results = filtered_election(seats, $param.keys)
    else
      # Initial display
      seats   = '9'
      results = filtered_election(seats, NOMINEES.map {|letter,name| letter})
    end

    # form of nominees and seats
    x.form :method => 'post', :id => 'vote' do
      NOMINEES.sort_by {|letter, name| name}.each do |letter, name|

        attrs = {:type=>'checkbox', :name=>letter, :id => letter}
        unless $param[letter].empty? and $param.keys.length>0
          attrs[:checked]='checked'
        end
        x.input attrs

        x.label name, :id=>name, :class=>results[name], :for=>letter
        x.br
      end

      x.label 'seats:', :for=>'seats'
      x.input :name=>'seats', :id=>'seats', :value=>seats, :size=>1
      x.br

      x.input :type=>'submit', :value=>'submit'
    end

    x.p do
      x.a 'Background Info', :href=>'http://wiki.apache.org/general/BoardVoting'
    end
  end
end

__END__
VOTER = '/home/rubys/tmp/Vote-0-4.jar'
