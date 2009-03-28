var boxes = [];
window.addEvent('domready', function(){
	boxes.push(new MultiBox('mb_login',
				{"descClassName": "multiBoxDesc", 
					"useOverlay": true}));
	boxes.push(new MultiBox('mb_logout_known', 
				{"descClassName": "multiBoxDesc", 
					"useOverlay": true}));
	boxes.push(new MultiBox('mb_logout_registered',
				{"descClassName": "multiBoxDesc", 
					"useOverlay": true}));
    });


dojo.require("dojo.rpc.JsonService");


var ws = new dojo.rpc.JsonService({
        "serviceType": "JSON-RPC",
        "serviceURL": "/ws",
        "timeout": 7200,
        "methods":[{"name": "validate", "parameters": [{"name": "code"}]},
                   {"name": "execute", "parameters": [{"name": "code"}]},
                   {"name": "get_account_status", "parameters": []},
		   {"name": "get_constants", "parameters": []}]
});


ws.get_constants().addCallback(function(CONSTANTS) {


var style_link = function(link)
{
    link.style.cursor = "pointer";
    link.style.color = "blue";
    link.style.textDecoration = "underline";
};


var set_text = function(node, text)
{
    dojo.forEach(node.childNodes, function(n) {
	    n.parentNode.removeChild(n);
	});
    var t = document.createTextNode(text);
    node.appendChild(t);
};


function refresh_account_status()
{
    var account_status = document.getElementById("account_status");
    var pending = document.getElementById("account_status_pending");
    var unknown = document.getElementById("account_unknown");
    var known = document.getElementById("account_known");
    var registered = document.getElementById("account_registered");
    pending.style.display = "";
    dojo.forEach([unknown, known, registered], function(i) {
	    i.style.display = "none";
	});
    dojo.forEach(boxes, function(i) {
	    if (i.opened)
		{
		    i.close();
		}
	});
    ws.get_account_status().addCallback(function(status) {
	    pending.style.display = "none";
	    if (status == "unknown")
		{
		    unknown.style.display = "";
		}
	    else if (status == "known")
		{
		    known.style.display = "";
		}
	    else if (status == "registered")
		{
		    registered.style.display = "";
		}
	    else
		{
		    throw new Error("Unknown status: " + status.toSource());
		}
	});
};
window.refresh_account_status = refresh_account_status;


var init = function() 
{
    refresh_account_status();
};


dojo.addOnLoad(init);

});
