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


var init = function()
{
    emulate_onhashchange();
    var cb = function(pages)
    {
	var ordered_names = [];
	var name_to_title = {};
	dojo.forEach(pages, function(item) {
		ordered_names.push(item[0]);
		name_to_title[item[0]] = item[1];
	    })
	var process_hash_change = function()
	{
	    var hash = read_hash();
	    if (typeof name_to_title[hash] == "undefined")
		{
		    throw new Error("Unknown page: " + hash.toSource());
		}
	    var handle_data = function(content)
	    {
		dojo.byId("tutorial-body").innerHTML = content;
	    };
	    var index = dojo.indexOf(ordered_names, hash);
	    var first = dojo.byId("first_link");
	    var previous = dojo.byId("previous_link");
	    if (index == 0)
		{
		    first.style.visibility = "hidden";
		    previous.style.visibility = "hidden";
		}
	    else
		{
		    var first_name = ordered_names[0];
		    first.setAttribute("title", name_to_title[first_name]);
		    first.setAttribute("href", "#" + first_name);
		    first.style.visibility = "visible";
		    var previous_name = ordered_names[index - 1];
		    previous.setAttribute("title", 
					  name_to_title[previous_name]);
		    previous.setAttribute("href", "#" + previous_name);
		    previous.style.visibility = "visible";
		}
	    var current = dojo.byId("current_title");
	    var title = "Online Python Tutorial - " + name_to_title[hash]
	    set_text(current, title);
	    document.title = title;
	    var next = dojo.byId("next_link");
	    var last = dojo.byId("last_link");
	    if (index == ordered_names.length - 1)
		{
		    next.style.visibility = "hidden";
		    last.style.visibility = "hidden";
		}
	    else
		{
		    var next_name = ordered_names[index + 1];
		    next.setAttribute("title", name_to_title[next_name]);
		    next.setAttribute("href", "#" + next_name);
		    next.style.visibility = "visible";
		    var last_name = ordered_names[ordered_names.length - 1];
		    last.setAttribute("title", name_to_title[last_name]);
		    last.setAttribute("href", "#" + last_name);
		    last.style.visibility = "visible";
		}
	    dojo.xhrGet({"url": "/static/" + hash}).addCallback(handle_data);
	};
	window.onhashchange = process_hash_change;
	if (read_hash() == null)
	    {
		write_hash(ordered_names[0], true);
	    }
	process_hash_change();
    };
    var params = {"url": "/static/tutorial-index.json", 
		  "handleAs": "json"}
    dojo.xhrGet(params).addCallback(cb);
};


dojo.addOnLoad(init);

