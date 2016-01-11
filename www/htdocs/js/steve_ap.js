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

function displayIssueAP(code, response, state) {
    election_data = response
    var obj = document.getElementById('preloaderWrapper')
    obj.setAttribute("id", "ynavote")
    if (code != 200) {
        obj.innerHTML = "<h1>Could not load issue:</h1><h2>" + response.message + "</h2>";
    } else {
        obj.innerHTML = ""
        
        var title = document.createElement('h2')
        title.innerHTML = response.issue.title;
        obj.appendChild(title)
        
        obj.appendChild(keyvaluepairText("nominatedby", "Put forward (nominated) by:", response.issue.nominatedby))
        obj.appendChild(keyvaluepairText("seconds", "Seconded by:", response.issue.seconds.length > 0 ?  response.issue.seconds.join(", ") : "no-one" ))
        
        var desc = document.createElement('pre')
        desc.setAttribute("class", "statement")
        desc.innerHTML = response.issue.description
        obj.appendChild(desc)
        
        var outer = document.createElement('div')
        outer.setAttribute("class", "issueListItemWide")
        
        var byes = document.createElement('input')
        byes.setAttribute("type", "button")
        byes.setAttribute("value", "Binding Yes (+1)")
        byes.setAttribute("class", "btn-green")
        byes.setAttribute("style", "float: right;");
        byes.setAttribute("onclick", "castSingleVote('by');")
        
        var yes = document.createElement('input')
        yes.setAttribute("type", "button")
        yes.setAttribute("value", "Yes (+1)")
        yes.setAttribute("class", "btn-green")
        yes.setAttribute("style", "float: right;");
        yes.setAttribute("onclick", "castSingleVote('y');")
        
        var no = document.createElement('input')
        no.setAttribute("type", "button")
        no.setAttribute("value", "No  (-1)")
        no.setAttribute("class", "btn-red")
        no.setAttribute("style", " float: right;");
        no.setAttribute("onclick", "castSingleVote('n');")
        
        var bno = document.createElement('input')
        bno.setAttribute("type", "button")
        bno.setAttribute("value", "Binding No (-1)")
        bno.setAttribute("class", "btn-red")
        bno.setAttribute("style", " float: right;");
        bno.setAttribute("onclick", "castSingleVote('bn');")
        
        var abstain = document.createElement('input')
        abstain.setAttribute("type", "button")
        abstain.setAttribute("value", "Abstain (0)")
        abstain.setAttribute("class", "btn-yellow")
        abstain.setAttribute("style", "float: right;");
        abstain.setAttribute("onclick", "castSingleVote('a');")
        
        var p = document.createElement('p')
        p.innerHTML = "Cast your vote by clicking on the respective button below. You may recast your vote as many time as you like, should you reconsider."
        
        obj.appendChild(p)
        outer.appendChild(bno)
        outer.appendChild(no)
        outer.appendChild(abstain)
        outer.appendChild(yes)
        outer.appendChild(byes)
        
        obj.appendChild(outer)
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
