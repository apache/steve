/*
 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements.  See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/

var step = -1
var election_data;
var vote_DH = null;

var candidates;
var chars;

// A little shuffle, so we don't all get the same order at first
function shuffleCandidates() {
    for (var i = 0; i < candidates.length; i++) {
        
        // Pick some numbers
        var sid = parseInt(Math.random()*candidates.length-0.01);
        var did = parseInt(Math.random()*candidates.length-0.01);
        
        // Splice!
        if (sid >= 0 && did >= 0) {
            candidates.splice(did, 0, candidates.splice(sid, 1)[0])
            chars.splice(did, 0, chars.splice(sid, 1)[0])
        }
    }
}

function loadIssue(election, issue, uid, callback) {
    
    var messages = ["Herding cats...", "Shaving yaks...", "Shooing some cows away...", "Fetching election data...", "Loading issues..."]
    if (!election || !uid) {
        var l = document.location.search.substr(1).split("/");
        election = l[0];
        issue = l.length > 1 ? l[l.length-2] : "";
        uid = l.length > 2 ? l[l.length-1] : "";
    }
    if (step == -1) {
        getJSON("/steve/voter/view/" + election + "/" + issue + "?uid=" + uid, [election, issue, uid], callback)
    }
    
    var obj = document.getElementById('preloader');
    step++;
    if (!election_data && obj) {
        if (step % 2 == 1) obj.innerHTML = messages[parseInt(Math.random()*messages.length-0.01)]
    } else if (obj && (step % 2 == 1)) {
        obj.innerHTML = "Ready..!"
    }
    if (step % 2 == 1) {
        obj.style.transform = "translate(0,0)"
    } else if (obj) {
        obj.style.transform = "translate(0,-500%)"
    }
    if (!election_data|| (step % 2 == 0) ) {
        window.setTimeout(loadElection, 750, election, uid, callback);
    }
}

function drawCandidatesDH() {
    var box = document.getElementById('candidates')
    box.innerHTML = "<h3>Candidates:</h3>"
    for (i in candidates) {
        var name = candidates[i]
        var char = chars[i]
        // Add element and set drag'n'drop + data
        var li = document.createElement('li')
        var outer = document.createElement('div')
        var inner = document.createElement('span')
        inner.style.fontFamily = "monospace"
        inner.innerHTML = char + ": " + name;
        inner.setAttribute("ondrop", "dropCandidate(event, true)")
        outer.setAttribute("class", "ballotbox_clist_DH")
        if (char == vote_DH) {
            outer.setAttribute("class", "ballotbox_clist_selectedDH")
        }
        outer.setAttribute("id", name)
        outer.setAttribute("onclick", "vote_DH = '"+char+"'; drawCandidatesDH();")
        outer.appendChild(inner)
        outer.setAttribute("title", "Click to select "  + name + " as your preference")
        li.appendChild(outer)
        // Does the candidate have a statement? if so, put it on there
        if (statements[char]) {
            var statement = document.createElement('div')
            statement.setAttribute("class", "statement_marker")
            statement.setAttribute("title", "Click to read " + name + "'s statement")
            statement.innerHTML = "<a href='#statement_"+char+"'>Statement</a>"
            
            li.appendChild(statement)
            
            var popup = document.createElement("div")
            popup.setAttribute("class", "modal")
            popup.setAttribute("id", "statement_" + char)
            popup.setAttribute("aria-hidden", "true")
            
            var popupd = document.createElement("div")
            popupd.setAttribute("class", "modal-dialog")
            popup.appendChild(popupd)
            
            var popuph = document.createElement("div")
            popuph.setAttribute("class", "modal-header")
            popuph.innerHTML = '<h2>Statement from ' + name + '</h2><a href="#close" class="btn-close" aria-hidden="true">�</a>'
            
            var popupb = document.createElement("div")
            popupb.setAttribute("class", "modal-body")
            popupb.innerHTML = '<pre>' + (statements[char] ? statements[char] : "This candidate has not prepared a statement") +'</pre>'
            
            var popupf = document.createElement("div")
            popupf.setAttribute("class", "modal-footer")
            popupf.innerHTML = '<a href="#close" class="btn">Close statement</a>'
            
            popupd.appendChild(popuph)
            popupd.appendChild(popupb)
            popupd.appendChild(popupf)
            
            document.getElementsByTagName('body')[0].appendChild(popup)
        }/* else {
            var statement = document.createElement('div')
            statement.setAttribute("class", "statement_marker")
            statement.style = "background: linear-gradient(to bottom, #e2e2e2 0%,#dbdbdb 50%,#d1d1d1 51%,#fefefe 100%) !important;"
            statement.style.color = "#666";
            statement.innerHTML = "<i>No statement</i>"

            outer.appendChild(statement)
        }*/
        box.appendChild(li)
        
    }
}

function displayIssueDH(code, response, state) {
    chars = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']  // Corresponding STV letters, in same order as nominees
    election_data = response
    if (code != 200) {
        document.getElementById('preloaderWrapper').innerHTML = "<h1>Could not load issue:</h1><h2>" + response.message + "</h2>";
    } else {
        candidates = []
        statements = {}
        var m = response.issue.type.match(/(\d+)/);
        if (m) {
            seats = parseInt(m[1])
        }
        for (c in response.issue.candidates) {
            var candidate = response.issue.candidates[c];
            candidates.push(candidate.name);
            statements[chars[c]] = candidate.statement;
        }
        if (document.getElementById('cnum')) document.getElementById('cnum').innerHTML = candidates.length
        if (document.getElementById('snum')) document.getElementById('snum').innerHTML = seats        
        while (chars.length > candidates.length) chars.splice(-1,1)
        
        
        var obj = document.getElementById('preloaderWrapper')
        obj.innerHTML = ""
        obj.setAttribute("style", "min-width: 100%; min-height: 400px;")
        obj.setAttribute("id", "votebox")
        
        if (response.issue.description) {
            var p = document.createElement('pre')
            p.innerHTML = response.issue.description.replace(/&lt;/g, "<")
            obj.appendChild(p)
        }
        
        var l = document.createElement('ol')
        l.setAttribute("id", "candidates")
        obj.appendChild(l)
        
        shuffleCandidates();
        drawCandidatesDH();
        
        
        var vote = document.createElement('input')
        vote.setAttribute("type", "button")
        vote.setAttribute("class", "btn-green")
        vote.setAttribute("value", "Cast vote")
        vote.setAttribute("onclick", "castVoteDH();")
        
        
        obj.appendChild(vote)
        
        document.getElementById('title').innerHTML = response.issue.title
        document.title = response.issue.title + " - Apache STeVe"
        
    }
    
}

function castVoteDH() {
    var l = document.location.search.substr(1).split("/");
    election = l[0];
    issue = l.length > 1 ? l[l.length-2] : "";
    uid = l.length > 2 ? l[l.length-1] : "";
    if (vote_DH) {
        postREST("/steve/voter/vote/" + election + "/" + issue, {
            uid: uid,
            vote: vote_DH
        },
        undefined,
        DHVoteCallback,
        null)
    } else {
        alert("Please select a preference first!")
    }
    
}

function DHVoteCallback(code, response, state) {
    if (code != 200) {
        alert(response.message)
    } else {
        document.getElementById('votebox').innerHTML = "<h2>Your vote has been registered!</h2><p style='text-align:center;'><big>Should you reconsider, you can always reload this page and vote again.<br/><br/><a href=\"javascript:void(location.href='election.html'+document.location.search);\">Back to election front page</a></big></p>"
    }
}