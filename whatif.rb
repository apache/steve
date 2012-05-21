# STV Explorer using Historical data from ASF Board Votes
#
# Prereqs:
#
#   * svn checkout of foundation:voter and foundation:Meetings
#   * Web server with the ability to run cgi (Apache httpd recommended)
#   * Python 2.6.x
#   * Ruby 1.9.x
#   * Java 1.1 or later
#   * Vote-0-4.jar from the vote-0-4.zip found at:
#       http://sourceforge.net/projects/votesystem/files/votesystem/0.4/
#   * wunderbar gem ([sudo] gem install wunderbar)
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

MEETINGS  = File.expand_path('../Meetings').untaint unless defined? MEETINGS
NSTV   = 'monitoring/nstv-rank.py'
FILTER = 'vote-filter.py'
VOTER  = '/home/rubys/tmp/Vote-0-4.jar' unless defined? VOTER

require 'wunderbar'
require 'tempfile'

def raw_votes(date)
  all_votes = Dir["#{MEETINGS}/*/raw_board_votes.txt"]
  if date
    result = "#{MEETINGS}/#{date}/raw_board_votes.txt"
  else
    result = all_votes.sort.last
  end
  result.untaint if all_votes.include? result
  result
end

def ini(vote)
  vote.sub('/raw_','/').sub('votes.','nominations.').sub('.txt','.ini')
end

def filtered_election(seats, candidates)
  list = candidates.join(' ')
  list.untaint if list =~ /^\w( \w)*$/
  seats.untaint if seats =~ /^\d+$/

  votes = Tempfile.new('votes', Dir.tmpdir.untaint)
  votes << `python #{NSTV} #{raw_votes(@date)} | python #{FILTER} #{list}`
  votes.flush
  output = `java -cp  #{VOTER} VoteMain -system stv-meek \
            -seats #{seats} #{votes.path}`
  output.scan(/.*elected$/).inject(Hash.new('none')) do |results, line|
    name, status = line.scan(/^(.*?)\s+(n?o?t?\s?elected)$/).flatten
    results.merge({name[0..8].gsub(/\W/,'') => status.gsub(/\s/, '-')})
  end
end

# XMLHttpRequest (AJAX)
_json do
  _! filtered_election(@seats, params.keys.select {|key| key =~ /^\w$/})
end

# main output
_html do
  _head_ do
    _title 'STV Explorer'
    _style! %{
       h1 {font-family: sans-serif; font-weight: normal}
       select {display: block; margin: 0 0 1em 1em; font-size: 140%}
       label div {display: inline-block; min-width: 12em; font-size: x-large}
       label div {-webkit-transition: background-color 1s}
       label div {-moz-transition: background-color 1s}
       label {float: left; clear: both}
       label[for=seats] {display: inline; line-height: 500%}
       p, input[type=checkbox] {margin-left: 1em}
       p, input[type=submit] {display: block; clear: both}
       .elected {background: #0F0}
       .not-elected {background: #F00}
       .none {background: yellow}
    }
    _script src: 'jquery.min.js'
  end

  _body? do
    _h1_ 'STV Explorer'

    nominees = Hash[File.read(ini(raw_votes(@date))).scan(/^(\w):\s*(.*)/)]
    candidates = params.keys & nominees.keys
    candidates = nominees.keys if candidates.empty? or @reset

    @seats ||= '9'
    results = filtered_election(@seats, candidates)

    # form of nominees and seats
    _form method: 'post', id: 'vote' do
      _select name: 'date' do
        Dir["#{MEETINGS}/*/raw_board_votes.txt"].sort.reverse.each do |votes|
	  next unless File.exist? ini(votes.untaint)
	  date = votes[/(\d+)\/raw_board_votes.txt$/,1]
          display = date.sub(/(\d{4})(\d\d)(\d\d)/,'\1-\2-\3')
          _option display, value: date, selected: (votes == raw_votes(@date))
	end
      end

      nominees.sort_by {|letter, name| name}.each do |letter, name|
        id = name[0..8].gsub(/\W/,'')
        _label_ id: id do
          _input type: 'checkbox', name: letter, id: letter, 
            checked: candidates.include?(letter)

          _div name, class: results[id]
        end
      end

      _label_ for: 'seats' do
        _span 'seats:'
        _input name: 'seats', id: 'seats', value: @seats, size: 1
      end

      _input type: 'submit', value: 'submit', name: 'submit'
    end

    _p_ do
      _a 'Background Info', href: 'http://wiki.apache.org/general/BoardVoting'
    end

    _script %{
      // submit form using XHR; update class for labels based on results
      var refresh = function() {
        $.getJSON('', $('#vote').serialize(), function(results) {
          for (var name in results) {
            $('#'+name+' div').attr('class', results[name]);
          }
        });
        return false;
      }

      // On checkbox click, remove class from associated label & refresh
      $(':checkbox').click(function() {
        $('div', $(this).parent()).attr('class', 'none');
        refresh();
      });

      // reset whenever the date changes
      $('select').change(function() {
        $('input[value=submit]').attr('name', 'reset');
        $('input[value=submit]').click();
      });

      // If JS is enabled, we don't need a submit button
      $('input[type=submit]').hide();

      // Add up and down arrows and refresh on change
      var seats = $('#seats');
      seats.keyup(function() {return refresh()});
      seats.before($('<button>&#x21D3;</button>').click(function() {
        if (seats.val()>1) {seats.val(seats.val()-1);}
        return refresh();
      }));
      seats.after($('<button>&#x21D1;</button>').click(function() {
        if (seats.val()<$(':checkbox').length) {seats.val(seats.val()-0+1);}
        return refresh();
      }));
    }
  end
end

__END__
VOTER = '/home/rubys/tmp/Vote-0-4.jar'
