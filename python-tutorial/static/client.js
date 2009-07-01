dojo.require("dojo.rpc.JsonService");


var ws = new dojo.rpc.JsonService({
        "serviceType": "JSON-RPC",
        "serviceURL": "/ws",
        "timeout": 7200,
        "methods":[{"name": "execute", "parameters": [{"name": "code"}]},
		   {"name": "get_constants", "parameters": []}]
});


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




var init = function() 
{
};


dojo.addOnLoad(init);

