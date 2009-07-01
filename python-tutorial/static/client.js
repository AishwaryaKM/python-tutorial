var boxes = [];
window.addEvent('domready', function(){
	boxes.push(new MultiBox('mb_login',
				{"descClassName": "multiBoxDesc", 
					"useOverlay": true}));
	boxes.push(new MultiBox('mb_logout_known', 
				{"descClassName": "multiBoxDesc", 
					"useOverlay": true}));
    });


dojo.require("dojo.rpc.JsonService");


var ws = new dojo.rpc.JsonService({
        "serviceType": "JSON-RPC",
        "serviceURL": "/ws",
        "timeout": 7200,
        "methods":[{"name": "execute", "parameters": [{"name": "code"}]},
//                    {"name": "get_account_status", "parameters": []},
		   {"name": "get_constants", "parameters": []}]
});


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


var write_out = function(output)
{
    set_text(document.getElementById("output"), output);
};


var execute = function()
{
  var code = document.getElementById("code").value;
  ws.execute(code).addCallback(write_out);
};


var fill_in_example = function()
{
    var cb = function(data)
    {
	document.getElementById("code").value = data;
    };
    dojo.xhrGet({"url": "/static/example.py"}).addCallback(cb);
};


function refresh_account_status()
{
    var account_status = document.getElementById("account_status");
    var pending = document.getElementById("account_status_pending");
    var unknown = document.getElementById("account_unknown");
    var known = document.getElementById("account_known");
    var user_id = document.getElementById("user_id");
    var registration = document.getElementById("user_registration");
    pending.style.display = "";
    dojo.forEach([unknown, known], function(i) {
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
	    if (status[0] == "unknown")
		{
		    unknown.style.display = "";
		}
	    else if (status[0] == "known")
		{
		    set_text(registration, status[1]);
		    set_text(user_id, status[2]);
		    known.style.display = "";
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
//     refresh_account_status();
};


dojo.addOnLoad(init);

