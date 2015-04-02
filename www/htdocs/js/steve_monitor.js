// Function for fetching JSON from the REST API
function getJSON(theUrl, xstate, callback) {
	var xmlHttp = null;
	if (window.XMLHttpRequest) {
		xmlHttp = new XMLHttpRequest();
	} else {
		xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
	}
	xmlHttp.open("GET", theUrl, true);
	xmlHttp.send(null);
	xmlHttp.onreadystatechange = function(state) {
		if (xmlHttp.readyState == 4 && xmlHttp.status && xmlHttp.status >= 200) {
			if (callback) {
				window.setTimeout(callback, 0.01, xmlHttp.status, (xmlHttp.responseText && xmlHttp.responseText.length > 1) ? JSON.parse(xmlHttp.responseText) : null, xstate);
			}
		}
	}
}

function getIssues() {
	election = document.location.search.substr(1)
	getJSON("/steve/admin/view/" + election, election, listIssues)
}

var ehash = null
var eid = null
var issues = []
var basedata = {}
var votes = {}
var oldvotes = {}
var recasts = {}
var recasters = {}
var rigged = false
var riggedIssues = {}

function listIssues(code, response, election) {
	if (code == 200) {
		eid = election
		issues = response.issues
		basedata = response.base_data
		document.getElementById('title').innerHTML += " " + basedata.title
		var obj = document.getElementById('preloaderWrapper')
		obj.innerHTML = ""
		obj.setAttribute("id", "contents")
		for (i in issues) {
			window.setTimeout(showChanges, 1000, issues[i])
		}
	} else {
		alert(response.message)
	}
}

function updateVotes(code, response, issue) {
	if (code == 200) {
		recasters[issue] = recasters[issue] ? recasters[issue] : {}
		oldvotes[issue] = votes[issue] ? votes[issue] : {}
		votes[issue] = response.votes
		var is = {}
		for (i in issues) {
			if (issues[i].id == issue) {
				is = issues[i]
				break
			}
		}
		if (is.hash && response.issue.hash != is.hash) {
			riggedIssues[issue] = "WAS: " + JSON.stringify(is) + " - IS NOW: " + JSON.stringify(response.issue)
		}
		if (ehash == null) {
			ehash = response.hash
		}
		if (ehash != response.hash) {
			rigged = true
		}
		recasts[issue] = recasts[issue] ? recasts[issue] : 0
	} else if (response.message == "Issue not found") {
		var header = document.getElementById('issue_' + issue + "_header")
		header.innerHTML = "<font color='red'><b>Issue deleted?: " + response.message + "</b></font>"
	}
}

function calcChanges(issue, oldv, newv) {
	sinceLast = 0;
	
	
	// Find new votes cast since last update
	if (!oldv || !newv) {
		return [0,0]
	}
	for (i in newv) {
		if (!oldv[i]) {
			sinceLast++;
		} else if (oldv[i].timestamp != undefined && newv[i].timestamp != undefined && oldv[i].timestamp != newv[i].timestamp) {
			recasts[issue]++;
			recasters[issue][i] = (recasters[issue][i] ? recasters[issue][i] : 0) + 1
		}
	}
	var nrc = 0;
	for (i in recasters[issue]) nrc++;
	
	return [sinceLast, nrc]
}

var timeouts = {}

function showDetails(issueid, update) {
	var obj = document.getElementById('issue_' + issueid + '_details')
	if (obj.innerHTML.length > 0 && !update) {
		obj.innerHTML = ""
		window.clearTimeout(timeouts[issueid])
	} else {
		obj.innerHTML = ""
		for (i in votes[issueid]) {
			var rawvote = votes[issueid][i]
			var vote = null
			var nrc = recasters[issueid][i] ? recasters[issueid][i] : 0
			var add = ""
			if (rawvote.timestamp) {
				vote = rawvote.vote
				add = ". Cast at " + new Date(rawvote.timestamp*1000).toLocaleString()
			} else {
				vote = rawvote
			}
			if (nrc > 0) {
				nrc = "Vote recast " + nrc + " time(s)"
			} else {
				nrc = "No recasts yet"
			}
			obj.innerHTML += "<b>" + i + ": </b> " + vote + " - " + nrc + add + "<br/>"
		}
		timeouts[issueid] = window.setTimeout(showDetails, 2500, issueid, true)
	}
	
}


function showChanges(issue) {
	var parent = document.getElementById('issue_' + issue.id)
	var header = document.getElementById('issue_' + issue.id + "_header")
	if (rigged) {
		document.getElementById('title').innerHTML = "<font color='red'>ELECTION HAS BEEN CHANGED SINCE IT OPENED, POSSIBLE RIGGING ATTEMPT!</font>"
	}
	if (!parent) {
		parent = document.createElement('div')
		parent.setAttribute("id", "issue_" + issue.id)
		parent.setAttribute("class", "monitor_issue")
		document.getElementById('contents').appendChild(parent)
		
		parent.innerHTML = "<h3>Issue #" + issue.id + ": " + issue.title + "</h3>"
		
		header = document.createElement('div')
		header.setAttribute("id", "issue_" + issue.id + "_header")
		header.innerHTML = "Awaiting vote data...hang on!"
		parent.appendChild(header)
		
		details = document.createElement('div')
		details.setAttribute("id", "issue_" + issue.id + "_details")
		details.setAttribute("class", "monitor_details")
		parent.appendChild(details)
		
		window.setTimeout(showChanges, 2000, issue)
	} else {
		window.setTimeout(showChanges, 15000, issue)
		numvotes = 0;
		if (votes[issue.id]) {
			for (i in votes[issue.id]) numvotes++;
		}
		if (numvotes > 0) {
			var v = votes[issue.id]
			var a = calcChanges(issue.id, oldvotes[issue.id], v)
			sinceLast = a[0]
			nrc = a[1]
			header.innerHTML = ""
			if (riggedIssues[issue.id] && riggedIssues[issue.id].length > 0) {
				header.innerHTML += "<a href='#' onclick=\"alert(riggedIssues['" + issue.id + "']);\"><font color='red'>ISSUE POSSIBLY RIGGED! </font></a><br/> "
			}
			header.innerHTML += numvotes + " votes cast, " + sinceLast + " new votes cast since last update. " + recasts[issue.id] + " votes have been recast, split among " + nrc + " voters."
			header.innerHTML += " <a href='javascript:void(showDetails(\"" + issue.id + "\"));'>Show details</a>"
			header.innerHTML += " &nbsp; <a href='/steve/admin/monitor/" + eid + "/" + issue.id + "' target='_blank'>Get JSON</a>"
		} else {
			header.innerHTML = "No votes cast yet..!"
		}
	}
	getJSON("/steve/admin/monitor/" + eid + "/" + issue.id, issue.id, updateVotes)
	
	
	
}


function disableF5(e) {
	if ((e.which || e.keyCode) == 116 || (e.which || e.keyCode) == 82) {
		e.preventDefault();
		alert("PLEASE...Do not refresh this page")
	}
}

window.onkeydown = disableF5