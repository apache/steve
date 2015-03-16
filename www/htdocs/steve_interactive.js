/* WARNING: This script contains Voodoo! */
/*
#####
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#####
*/

var ballotNames = []
var ballotChars = []
var chars = chars? chars : ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']  // Corresponding STV letters, in same order as nominees
var fading = false
// Cut away unused chars
while (chars.length > candidates.length) chars.splice(-1,1)

// Make copies for reset
var candidates_copy = []
var chars_copy = []

var failover = null;

for (i in candidates) candidates_copy.push(candidates[i])
for (i in chars) chars_copy.push(chars[i])


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

function reset() {
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
        alert(source + ":" + dest)
    }
    //ev.preventDefault();
    // Redraw and carry on
    
    drawList()
    fadeIn(0, z)
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
            popuph.innerHTML = '<h2>Statement from ' + name + '</h2><a href="#close" class="btn-close" aria-hidden="true">×</a>'
            
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
        box.appendChild(outer)
        
    }
}

// Did we drop a vote on top of another?
function dropCandidate(ev) {
    
    ev.preventDefault();
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
        
        fadeIn(0, "ballot")
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
        fadeIn(0, "candidates")
        
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
        inner.innerHTML = ballotChars[i] + ": " + el;
        inner.setAttribute("ondrop", "dropVote(event, true)")
        outer.setAttribute("id", el)
        outer.setAttribute("data", el)
        inner.setAttribute("data", el)
        outer.setAttribute("draggable", "true")
        outer.setAttribute("ondragstart", "dragVote(event)")
        outer.setAttribute("ondragenter", "showLines(event)")
        outer.appendChild(inner)
        outer.setAttribute("title", "Drag to move "  + el + " up or down on the list")
        outer.setAttribute("ondrop", "dropVote(event, false)")
        
        
        if (el == source) {
            outer.style.transform = "scaleY(0)"
            outer.style.minHeight = "0px"
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
    
    // Set the current STV order
    document.getElementById('cast').style.width = (chars_copy.length * 8)+ "px"
    document.getElementById('cast').value = ballotChars.join("")
}


// Fade in/out maneuvres
function fadeOut(x) {
    if (source) {
        if (!x) {
            x = 1
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

function fadeIn(x, y) {
    if (source) {
        x += 0.1
        if (x >= 1) {
            x = 1
        }
        document.getElementById(source).style.opacity = String(x)
        document.getElementById(source).style.height = (x*22) + "px"
        document.getElementById(source).style.fontSize = (x*16) + "px"
        document.getElementById(source).style.transform = "scaleY(" + x + ")"
        
        
        document.getElementById(source).setAttribute("class", "ballotSelected")
        if (x < 1) {
            fading = true
            window.setTimeout(function() { fadeIn(x, y)}, 25)
            
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
