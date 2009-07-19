dojo.require("dojo.rpc.JsonService");


var ws = new dojo.rpc.JsonService({
        "serviceType": "JSON-RPC",
        "serviceURL": "/ws",
        "timeout": 7200,
        "methods":[{"name": "execute", "parameters": [{"name": "code"}]},
		   {"name": "get_constants", "parameters": []}]
});


var clear_element = function(node)
{
    dojo.forEach(node.childNodes, function(n) {
	    n.parentNode.removeChild(n);
	});
};


var set_text = function(node, text)
{
    clear_element(node);
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


var emulate_onhashchange = function()
{
    /*
     * There are probably quite a few implementations of this out
     * there already but so far every one I have found makes things
     * complicated and refers to browser history.  True, one of the
     * main features of this onhashchange event is to "fix" the back
     * button for some web applications but it should also fix
     * bookmark navigation, users who know the URL to type, URLs sent
     * via email, browsers that load tabs automatically on startup
     * etc.
     * 
     * One day I will find a cross-platform implementation of
     * something like this but for now it is easier to write it
     * myself.  When my application is further through development I
     * will need to make sure that it works on a wider range of
     * browsers but for now I am only testing using Firefox 3.5.  This
     * will include detecting whether the browser natively supports
     * the onhashchange event (currently just IE8) and skipping the
     * emulation.
     *
     * Notice that I have built a layer /on top/ of this very simple
     * onhashchange event.  I consider this to be application specific
     * logic because not all applications will use the fragment part
     * of the URL to identify objects and documents in the way that I
     * am here.
     */
    var hash = read_hash();
    if (typeof window.onhashchange == "undefined")
	{
	    window.onhashchange = function() {};
	}
    var maybe_fire_onhashchange = function()
    {
	var another_hash = read_hash();
	if (another_hash != hash)
	    {
		hash = another_hash;
		window.onhashchange();
	    }
    };
    window.setInterval(maybe_fire_onhashchange, 100);
};


var read_hash = function()
{
    /*
     * This is how I think fragment identifiers ought to look:
     *    http://example.com/something?q=1      - null
     *    http://example.com/something?q=1#     - ""
     *    http://example.com/something?q=1#hash - "hash"
     * That's fairly simple, I think.
     * I do know about window.location.hash but it works differently.
     */
    var location = "" + window.location;
    var index = location.indexOf("#");
    if (index == -1)
	{
	    return null;
	}
    else
	{
	    return location.substr(index + 1);
	}
};


var write_hash = function(new_hash, do_redirect)
{
    if (typeof new_hash != "string")
	{
	    /* 
	     * Not every possible return value from read_hash() is a valid
	     * input value to write_hash().
	     */
	    throw new Error("Requested a hash change which is not a string: "
			    + new_hash.toSource());
	}
    var location = "" + window.location;
    var index = location.indexOf("#");
    if (index == -1)
	{
	    var new_location = location + "#" + new_hash;
	}
    else
	{
	    var new_location = location.substr(0, index) + "#" + new_hash;
	}
    if (do_redirect)
	{
	    window.location.replace(new_location);
	}
    else
	{
	    window.location = new_location;
	}
};


var process_hash_change = function()
{
    read_hash();
    var node = document.getElementById("latest_hash_contents");
    clear_element(node);
    var hash = read_hash();
    if (hash == null)
	{
	    var child = document.createElement("em");
	    node.appendChild(child);
	    set_text(child, "[no hash]");
	}
    if (hash == "")
	{
	    var child = document.createElement("em");
	    node.appendChild(child);
	    set_text(child, "[empty string]");
	}
    else
	{
	    set_text(node, hash);
	}
};


var init = function()
{
    emulate_onhashchange();
    window.onhashchange = process_hash_change;
    if (read_hash() == null)
	{
	    write_hash("home", true);
	}
    process_hash_change();
};


dojo.addOnLoad(init);

