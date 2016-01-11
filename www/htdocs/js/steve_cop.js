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
var vote_COP = null;

var candidates;
var chars;


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


function drawCandidatesCOP() {
    var box = document.getElementById('candidates')
    box.innerHTML = "<h3>Candidates:</h3>"
    var pname = null
    var pli = null;
    for (i in candidates) {
        var name = candidates[i]
        if (pname != name['pname']) {
            pname = name['pname']
            var char = name['pletter']
            pli = document.createElement('ol')
            pli.setAttribute("class", "showList")
            pli.style.marginTop = "20px"
            var outer = document.createElement('div')
            var inner = document.createElement('span')
            inner.style.fontFamily = "monospace"
            inner.style.fontWeigth = "bold"
            inner.innerHTML = name['pname'];
            outer.setAttribute("class", "ballotbox_clist_DH")
            if (char == vote_COP) {
                outer.setAttribute("class", "ballotbox_clist_selectedDH")
            }
            outer.setAttribute("id", name)
            outer.setAttribute("onclick", "vote_COP = '"+char+"'; drawCandidatesCOP();")
            outer.appendChild(inner)
            outer.setAttribute("title", "Click to select "  + name + " as your preference")
            pli.appendChild(outer)
            box.appendChild(pli)
            
        }
        var char = name['letter']
        var li = document.createElement('li')
        var outer = document.createElement('div')
        var inner = document.createElement('span')
        inner.style.fontFamily = "monospace"
        li.style.marginLeft = "30px"
        li.style.marginBottom = "10px"
        inner.innerHTML = name['name'];
        outer.setAttribute("class", "ballotbox_clist_DH")
        if (char == vote_COP) {
            outer.setAttribute("class", "ballotbox_clist_selectedDH")
        }
        outer.setAttribute("id", name)
        outer.setAttribute("onclick", "vote_COP = '"+char+"'; drawCandidatesCOP();")
        outer.appendChild(inner)
        outer.setAttribute("title", "Click to select "  + name + " as your preference")
        li.appendChild(outer)
       
        pli.appendChild(li)
        
    }
}

function displayIssueCOP(code, response, state) {
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
            candidates.push(candidate);
        }
        if (document.getElementById('cnum')) document.getElementById('cnum').innerHTML = candidates.length
        if (document.getElementById('snum')) document.getElementById('snum').innerHTML = seats        
        while (chars.length > candidates.length) chars.splice(-1,1)
        
        
        var obj = document.getElementById('preloaderWrapper')
        obj.innerHTML = ""
        obj.setAttribute("id", "contents")
        
        
        var l = document.createElement('ol')
        l.setAttribute("id", "candidates")
        l.setAttribute("type", "a")
        l.setAttribute("class", "showList")
        obj.appendChild(l)
        
        drawCandidatesCOP();
        
        
        var vote = document.createElement('input')
        vote.setAttribute("type", "button")
        vote.setAttribute("class", "btn-green")
        vote.setAttribute("value", "Cast vote")
        vote.setAttribute("onclick", "castVoteCOP();")
        
        
        obj.appendChild(vote)
        
        document.getElementById('title').innerHTML = response.issue.title
        document.title = response.issue.title + " - Apache STeVe"
        
    }
    
}

function castVoteCOP() {
    var l = document.location.search.substr(1).split("/");
    election = l[0];
    issue = l.length > 1 ? l[l.length-2] : "";
    uid = l.length > 2 ? l[l.length-1] : "";
    if (vote_COP) {
        postREST("/steve/voter/vote/" + election + "/" + issue, {
            uid: uid,
            vote: vote_COP
        },
        undefined,
        COPVoteCallback,
        null)
    } else {
        alert("Please select a preference first!")
    }
    
}

function COPVoteCallback(code, response, state) {
    if (code != 200) {
        alert(response.message)
    } else {
        document.getElementById('contents').innerHTML = "<h2>Your vote has been registered!</h2><p style='text-align:center;'><big>Should you reconsider, you can always reload this page and vote again.<br/><br/><a href=\"javascript:void(location.href='election.html'+document.location.search);\">Back to election front page</a></big></p>"
    }
}