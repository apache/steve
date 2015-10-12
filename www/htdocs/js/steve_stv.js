/* WARNING: This script contains Voodoo! */
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

var candidates = []
var statements = []
var seconds_txt = []
var ballotNames = []
var ballotChars = []
var chars;
var fading = false
var seats = 0;
var maxnum = 9999

// Make copies for reset
var candidates_copy = []
var chars_copy = []

var failover = null;



// Set transfer data during drag'n'drop
function dragVote(ev) {
    ev.dataTransfer.setData("Text", ev.target.getAttribute("data"));
    failover = ev.target.getAttribute("data")
    if (ballotNames.indexOf(failover) == -1) {
        document.getElementById('candidates').style.backgroundImage = "url(/images/dragright.png)"
        document.getElementById('candidates').style.backgroundRepeat = "no-repeat"
    } else {
        document.getElementById('candidates').style.backgroundImage = "url(/images/dragleft.png)"
        document.getElementById('candidates').style.backgroundRepeat = "no-repeat"
    }
}

var source, dest

function cancel(ev) {
    ev.preventDefault()
}

function resetList() {
    candidates = []
    chars = []
    for (i in candidates_copy) candidates.push(candidates_copy[i])
    for (i in chars_copy) chars.push(chars_copy[i])
    ballotNames = []
    ballotChars = []
    shuffleCandidates();
    
    drawCandidates()
    fading = false
    document.getElementById('ballot').innerHTML = '<img src="/images/target.png" style="margin-left: 100px;" ondrop="event.preventDefault(); dropCandidate(event);"/>';
    drawList();
}

// Did we drop a vote on top of another?
function dropVote(ev, parent) {
    
    //ev.preventDefault();
    if (parent || fading) return;
    
    // Get who we dragged and who we dropped it on
    source = ev.dataTransfer.getData("Text");
    dest = parent ? ev.target.parentNode.getAttribute("data") : ev.target.getAttribute("data")
    if (dest == "UPPER") { dest = ballotNames[0]}
    if (dest == "LOWER") { dest = ballotNames[ballotNames.length -1] }
    if (candidates.indexOf(dest) != -1) {
        alert("Back to school!")
    }
    
    // If we didn't drag this onto ourselves, let's initiate the fade-out and swap
    if (source != dest) {
        fadeOut(1, "ballot");
    }
    
}

function dropComplete(z) {
    if (fading) {
        return;
    }
    // Get array indices
    var sid = ballotNames.indexOf(source);
    var did = ballotNames.indexOf(dest)
    
    // Splice!
    if (sid >= 0 && did >= 0) {
        ballotNames.splice(did, 0, ballotNames.splice(sid, 1)[0])
        ballotChars.splice(did, 0, ballotChars.splice(sid, 1)[0])
    } else {
        //alert(source + ":" + dest)
    }
    //ev.preventDefault();
    // Redraw and carry on
    
    drawList()
    fadeIn(0, z, Math.random())
}


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


function drawCandidates() {
    var box = document.getElementById('candidates')
    box.innerHTML = "<h3>Candidates:</h3>"
    for (i in candidates) {
        var name = candidates[i]
        var char = chars[i]
        // Add element and set drag'n'drop + data
        var outer = document.createElement('div')
        var inner = document.createElement('span')
        inner.style.fontFamily = "monospace"
        inner.innerHTML = char + ": " + name;
        inner.setAttribute("ondrop", "dropCandidate(event, true)")
        outer.setAttribute("class", "ballotbox_clist")
        outer.setAttribute("id", name)
        outer.setAttribute("data", name)
        inner.setAttribute("data", name)
        outer.setAttribute("draggable", "true")
        outer.setAttribute("ondragstart", "dragVote(event)")
        outer.appendChild(inner)
        outer.setAttribute("title", "Drag to move "  + name + " to the ballot box")
        outer.setAttribute("ondrop", "dropCandidate(event, false)")
        outer.setAttribute("ondragover", "event.preventDefault();")
        outer.setAttribute("ondragend", "event.preventDefault();")
        outer.setAttribute("ondragenter", "event.preventDefault();")
        
        // Does the candidate have a statement? if so, put it on there
        if (statements[char]) {
            var statement = document.createElement('div')
            statement.setAttribute("class", "statement_marker")
            statement.setAttribute("title", "Click to read " + name + "'s statement")
            statement.innerHTML = "<a href='#statement_"+char+"'>Statement</a>"

            outer.appendChild(statement)
            
            var popup = document.createElement("div")
            popup.setAttribute("class", "modal")
            popup.setAttribute("id", "statement_" + char)
            popup.setAttribute("aria-hidden", "true")
            
            var popupd = document.createElement("div")
            popupd.setAttribute("class", "modal-dialog")
            popup.appendChild(popupd)
            
            var popuph = document.createElement("div")
            popuph.setAttribute("class", "modal-header")
            popuph.innerHTML = '<h2>Statement from ' + name + '</h2><a href="#close" class="btn-close" aria-hidden="true">&#00D7;</a>'
            
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
        }
        
        // Does the candidate have a nomination and/or seconds? if so, put it on there
        if (seconds_txt[char]) {
            var seconds = document.createElement('div')
            seconds.setAttribute("class", "statement_marker")
            seconds.setAttribute("title", "Click to read " + name + "'s nomination and/or seconds")
            seconds.innerHTML = "<a href='#statement_"+char+"'>2nds</a>"

            outer.appendChild(statement)
            
            var popup = document.createElement("div")
            popup.setAttribute("class", "modal")
            popup.setAttribute("id", "statement_" + char)
            popup.setAttribute("aria-hidden", "true")
            
            var popupd = document.createElement("div")
            popupd.setAttribute("class", "modal-dialog")
            popup.appendChild(popupd)
            
            var popuph = document.createElement("div")
            popuph.setAttribute("class", "modal-header")
            popuph.innerHTML = '<h2>Statement from ' + name + '</h2><a href="#close" class="btn-close" aria-hidden="true">&#00D7;</a>'
            
            var popupb = document.createElement("div")
            popupb.setAttribute("class", "modal-body")
            popupb.innerHTML = '<pre>' + (seconds[char] ? seconds[char] : "This candidate does not have a nomination statement") +'</pre>'
            
            var popupf = document.createElement("div")
            popupf.setAttribute("class", "modal-footer")
            popupf.innerHTML = '<a href="#close" class="btn">Close window</a>'
            
            popupd.appendChild(popuph)
            popupd.appendChild(popupb)
            popupd.appendChild(popupf)
            
            document.getElementsByTagName('body')[0].appendChild(popup)
        }
        box.appendChild(outer)
        
    }
}

// Did we drop a vote on top of another?
function dropCandidate(ev) {
    ev.preventDefault();
    if (ballotNames.length >= maxnum) {
        return; // MNTV lockout
    }
    source = ev.dataTransfer.getData("Text");
    dest = ev.target.getAttribute("data")
    var z = 0;
    if (dest == "UPPER") { dest = ballotNames[0]; z = 0}
    if (dest == "LOWER") { dest = ballotNames[ballotNames.length -1]; z = 1;}
    if (dest && candidates.indexOf(dest) != -1) {
        return;
    }
    if (ballotNames.indexOf(source) == -1 && candidates.indexOf(source) != -1) {
        var x = ballotNames.indexOf(dest)
        x += z
        if (ballotNames.indexOf(dest) != -1) {
            ballotNames.splice(x,0,source);
            ballotChars.splice(x,0,chars[candidates.indexOf(source)]);
        } else {
            ballotNames.push(source)
            ballotChars.push(chars[candidates.indexOf(source)])
        }
        chars.splice(candidates.indexOf(source), 1)
        candidates.splice(candidates.indexOf(source), 1)
        
        fadeIn(0, "ballot", Math.random())
        //ev.preventDefault()
        drawCandidates();
        drawList();
        
    }
    
}

// Did we drop a vote on top of another?
function dropBack(ev) {
    ev.preventDefault();
    source = ev.dataTransfer.getData("Text");
    dest = ev.target.getAttribute("data")
    
    if (dest == "UPPER") { dest = ballotNames[0]}
    if (dest == "LOWER") { dest = ballotNames[ballotNames.length -1] }
    
    if ((!dest || candidates.indexOf(dest) != -1) && ballotNames.indexOf(source) != -1) {
    
        candidates.push(source)
        chars.push(ballotChars[ballotNames.indexOf(source)])
        ballotChars.splice(ballotNames.indexOf(source), 1)
        ballotNames.splice(ballotNames.indexOf(source), 1)
        drawList();
        drawCandidates();
        fadeIn(0, "candidates", Math.random())
        
    } else {
        dest = null
        source = null
    }
}

function showLines(ev) {
    
    source = ev.dataTransfer.getData("Text");
    source = source ? source : failover;
    ev.preventDefault();
    if (ev.target) {
        var above = false
        dest = ev.target.getAttribute("data")
        var odest = dest;
        var override = false
        if (dest == "UPPER") { dest = ballotNames[0]; override = true; above = true;}
        if (dest == "LOWER") { dest = ballotNames[ballotNames.length-1]; override = true; above= false; }
        for (i=0;i< document.getElementById('ballot').childNodes.length;i++) {
            var el = document.getElementById('ballot').childNodes[i]
            el.style.borderTop = ""
            el.style.borderBottom = ""
        }
        document.getElementById('UPPER').style.borderTop = "none"
        document.getElementById('LOWER').style.borderBottom = "none"
        document.getElementById('UPPER').style.borderBottom = "none"
        document.getElementById('LOWER').style.borderTop = "none"
        if (ballotNames.indexOf(dest) != -1 && dest != source) {
            a = ballotNames.indexOf(source);
            b = ballotNames.indexOf(dest);
            
            override = false
            if (a != -1 && !override) {
                
                if (a > b) {
                    above = true;
                } else {
                    above = false;
                }
            } else {
                b--;
                if (b == -1) {
                    above = false;
                } if (b == ballotNames.length-1) {
                    above = false;
                }
            }
            
            if (((a == -1 || above == true) && odest != "UPPER") || odest == "LOWER") {
                document.getElementById(odest).style.borderTop = "16px solid #0AF";
            } else {
                document.getElementById(odest).style.borderBottom = "16px solid #0AF";
            }
        }
    }
    
}

function insertAfter(newNode, referenceNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

function insertBefore(newNode, referenceNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode);
}

function drawList() {
    
    
    // Remove drag helper
    document.getElementById('candidates').style.background = "";
    
    // Fetch ballot master and clear it
    var ballot = document.getElementById('ballot')
    ballot.innerHTML = ""
    var s = 0;
    
    // For each nominee, do...
    for (i in ballotNames) {
        s++;
        var el = ballotNames[i];
        var outer = document.createElement('li');
        // Set style
        outer.setAttribute("class", "ballotbox")
        
        var no = document.createElement('div');
        no.setAttribute("class", "ballotNumber")
        no.innerHTML = (s)
        
        
        // Above/below cutaway line? If so, draw it
        if (s == seats) {
            outer.style.borderBottom = "1px solid #A00"
        }
        if (s == seats+1) {
            outer.style.borderTop = "1px solid #A00"
        }
        
        // 'grey out' people below cutaway line
        if (s > seats) {
            outer.style.opacity = "0.75"
        }
        
        // Add element and set drag'n'drop + data
        var inner = document.createElement('span')
        inner.style.left = "35px"
        inner.style.maxWidth = "300px"
        inner.style.maxHeight = "60px"
        inner.style.overflow = "hidden"
        inner.innerHTML = ballotChars[i] + ": " + el;
        inner.setAttribute("ondrop", "dropVote(event, true)")
        outer.setAttribute("id", el)
        outer.setAttribute("data", el)
        inner.setAttribute("data", el)
        outer.setAttribute("draggable", "true")
        outer.setAttribute("ondragstart", "dragVote(event)")
        outer.setAttribute("ondragenter", "showLines(event)")
        outer.appendChild(no)
        outer.appendChild(inner)
        outer.setAttribute("title", "Drag to move "  + el + " up or down on the list")
        outer.setAttribute("ondrop", "dropVote(event, false)")
        
        
        if (el == source) {
            outer.style.opacity = "0"
        }
        
        // Add to box
        ballot.appendChild(outer)
    }
    
    // Drop upper and lower filler boxes, so people can drag to the top/bottom of the list as well
    if (!document.getElementById('UPPER')) {
        var d = document.createElement('div');
        d.setAttribute("class", "fillerbox")
        d.setAttribute("data", "UPPER");
        d.setAttribute("id", "UPPER");
        d.setAttribute("ondragenter", "showLines(event)")
        d.setAttribute("ondrop", "dropVote(event, false)")
        insertBefore(d, ballot);
        
        var d = document.createElement('div');
        d.setAttribute("class", "fillerbox")
        d.setAttribute("id", "LOWER")
        d.setAttribute("data", "LOWER");
        d.setAttribute("ondrop", "dropVote(event, false)")
        d.setAttribute("ondragenter", "showLines(event)")
        insertAfter(d, ballot);
    }
    
    // Clear any bad lines
    document.getElementById('UPPER').style.borderTop = "none"
    document.getElementById('LOWER').style.borderBottom = "none"
    document.getElementById('UPPER').style.borderBottom = "none"
    document.getElementById('LOWER').style.borderTop = "none"
    
}


// Fade in/out maneuvres
function fadeOut(x) {
    if (source) {
        if (!x) {
            x = 1
        }
        if (fading) {
            return;
        }
        x -= 0.1
        document.getElementById(source).setAttribute("class", "ballotSelected")
        document.getElementById(source).style.opacity = String(x)
        if (x > 0) {
            window.setTimeout(function() { fadeOut(x)}, 20)
        } else {
            dropComplete("candidates");
        }
    }   
}

var gz = 0;
function fadeIn(x, y, z) {
    if (source) {
        if (x == 0) {
            gz = z;
        }
        if (z != gz) {
            return;
        }
        x += 0.1
        if (x >= 1) {
            x = 1
        }
        document.getElementById(source).style.opacity = String(x)
        
        
        document.getElementById(source).setAttribute("class", "ballotSelected")
        if (x < 1) {
            fading = true
            window.setTimeout(function() { fadeIn(x, y, z)}, 25)
            
        } else {
             window.setTimeout(function() {fading = false }, 250)
            if (y == "ballot") {
                document.getElementById(source).setAttribute("class", "ballotbox")
                
            } else {
                document.getElementById(source).setAttribute("class", "ballotbox_clist")
                
            }
            source = null
            drawList();
            
            
        }
    }   
}

var step = -1

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

function displayIssueSTV(code, response, state) {
    chars = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']  // Corresponding STV letters, in same order as nominees
    election_data = response
    if (code != 200) {
        document.getElementById('preloaderWrapper').innerHTML = "<h1>Could not load issue:</h1><h2>" + response.message + "</h2>";
    } else {
        candidates = []
        seconds_txt = []
        statements = {}
        var m = response.issue.type.match(/(\d+)/);
        if (m) {
            seats = parseInt(m[1])
            if (response.issue.type.match(/mntv/) || response.issue.type.match(/fic/)) {
                maxnum = seats
            }
        }
        for (c in response.issue.candidates) {
            var candidate = response.issue.candidates[c];
            candidates.push(candidate.name);
            statements[chars[c]] = candidate.statement;
            seconds_txt[chars[c]] = candidate.seconds_txt; // don't use .seconds, that's for arrays!
        }
        document.getElementById('cnum').innerHTML = candidates.length
        document.getElementById('snum').innerHTML = seats        
        while (chars.length > candidates.length) chars.splice(-1,1)
        
        for (i in candidates) candidates_copy.push(candidates[i])
        for (i in chars) chars_copy.push(chars[i])


        var obj = document.getElementById('preloaderWrapper')
        obj.innerHTML = ""
        obj.setAttribute("style", "min-width: 100%; min-height: 400px;")
        obj.setAttribute("id", "ballotWrapper")
        
        
        var c = document.createElement('div')
        c.setAttribute("id", "candidates")
        c.setAttribute("ondragover", "event.preventDefault();")
        c.setAttribute("ondragenter", "event.preventDefault();")
        c.setAttribute("ondragend", "event.preventDefault();")
        c.setAttribute("ondrop", "dropBack(event);")
        obj.appendChild(c)
        
        var b = document.createElement('div')
        b.setAttribute("id", "ballotbox")
        b.setAttribute("ondragover", "event.preventDefault();")
        b.setAttribute("ondragenter", "event.preventDefault();")
        b.setAttribute("ondragend", "event.preventDefault();")
        b.setAttribute("ondrop", "dropCandidate(event);")
        b.innerHTML = "<font color='red'><h3>Drag candidates over here:</h3</font>"
        
        var l = document.createElement('ol')
        l.setAttribute("id", "ballot")
        b.appendChild(l)
        obj.appendChild(b)
        l.innerHTML = "<img src='/images/target.png'/>"
        
        
        var stvdiv = document.createElement('div')
        stvdiv.setAttribute("id", "stv")
        b.appendChild(stvdiv)
        
        var vote = document.createElement('input')
        vote.setAttribute("type", "button")
        vote.setAttribute("class", "btn-green")
        vote.setAttribute("value", "Cast votes")
        vote.setAttribute("onclick", "castVotes();")
        
        var reset = document.createElement('input')
        reset.setAttribute("type", "button")
        reset.setAttribute("class", "btn-red")
        reset.setAttribute("value", "Reset")
        reset.setAttribute("onclick", "resetList();")
        
        stvdiv.appendChild(vote)
        stvdiv.appendChild(reset)
        
        shuffleCandidates();
        drawCandidates();
        
        document.getElementById('title').innerHTML = response.issue.title
        document.title = response.issue.title + " - Apache STeVe"
        
    }
    
}

function castVotes(args) {
    var l = document.location.search.substr(1).split("/");
    election = l[0];
    issue = l.length > 1 ? l[l.length-2] : "";
    uid = l.length > 2 ? l[l.length-1] : "";
	postREST("/steve/voter/vote/" + election + "/" + issue, {
        uid: uid,
        vote: ballotChars.join("")
        },
        undefined,
        castVotesCallback,
        null)
}

function castVotesCallback(code, response, state) {
    if (code != 200) {
        alert(response.message)
    } else {
        document.getElementById('votebox').innerHTML = "<h2>Your vote has been registered!</h2><p style='text-align:center;'><big>Should you reconsider, you can always reload this page and vote again.<br/><br/><a href=\"javascript:void(location.href='election.html'+document.location.search);\">Back to election front page</a></big></p>"
    }
}

