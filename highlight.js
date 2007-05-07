var newlineElements = setObject("P", "DIV", "LI");

function simplifyDOM(root) {
  var doc = root.ownerDocument;
  var current = root;
  var result = [];
  var leaving = false;

  function simplifyNode(node) {
    leaving = false;

    if (node.nodeType == 3) {
      simplifyText(node);
    }
    else if (node.nodeName == "BR" && node.childNodes.length == 0) {
      result.push(node);
    }
    else {
      forEach(node.childNodes, simplifyNode);
      if (!leaving && node.nodeName in newlineElements) {
        leaving = true;
        result.push(withDocument(doc, BR));
      }
    }
  }

  function simplifyText(node) {
    var text = node.nodeValue;
    if (text.indexOf("\r") != -1)
      text = node.nodeValue = text.replace("\r", "");
    if (text == "")
      return;

    if (text.indexOf("\n") == -1) {
      result.push(node);
      return;
    }

    var lines = text.split("\n");
    for (var i = 0; i != lines.length; i++) {
      if (i > 0){
        var br = withDocument(doc, BR);
        replaceSelection(node, br, 1);
        result.push(br);
      }
      var line = lines[i];
      if (line.length > 0) {
        var textNode = doc.createTextNode(line);
        replaceSelection(node, textNode, line.length);
        result.push(textNode);
      }
    }
  }

  simplifyNode(root);
  return result;
}

function traverseDOM(start){
  function yield(value, c){cc = c; return value;}
  function push(fun, arg, c){return function(){return fun(arg, c);};}
  function chain(fun, c){return function(){fun(); return c();};}
  var cc = push(scanNode, start, function(){throw StopIteration;});
  var owner = start.ownerDocument;

  function pointAt(node){
    var parent = node.parentNode;
    var next = node.nextSibling;
    if (next)
      return function(newnode){parent.insertBefore(newnode, next);};
    else
      return function(newnode){parent.appendChild(newnode);};
  }
  var point = null;

  function insertPart(part){
    var text = "\n";
    if (part.nodeType == 3) {
      var text = part.nodeValue;
      part = withDocument(owner, partial(SPAN, {"class": "part"}, part));
      part.text = text;
    }
    part.dirty = true;
    point(part);
    return text;
  }

  function writeNode(node, c){
    var toYield = map(insertPart, simplifyDOM(node));
    for (var i = toYield.length - 1; i >= 0; i--)
      c = push(yield, toYield[i], c);
    return c();
  }

  function partNode(node){
    if (node.nodeName == "SPAN" && node.childNodes.length == 1 && node.firstChild.nodeType == 3){
      node.text = node.firstChild.nodeValue;
      return node.text.length > 0;
    }
    return false;
  }
  function newlineNode(node){
    return node.nodeName == "BR";
  }

  function scanNode(node, c){
    if (node.nextSibling)
      c = push(scanNode, node.nextSibling, c);
    if (partNode(node)){
      return yield(node.text, c);
    }
    else if (newlineNode(node)){
      return yield("\n", c);
    }
    // The check for parentNode is a hack to prevent weird problem in
    // FF where empty nodes seem to spontaneously remove themselves
    // from the DOM tree.
    else if (node.parentNode) {
      point = pointAt(node);
      removeElement(node);
      return writeNode(node, c);
    }
  }

  return {next: function(){return cc();}};
}

var atomicTypes = setObject("atom", "number", "variable", "string", "regexp");  

function parse(tokens){
  var cc = [statements];
  var consume, markdef;
  var context = null;
  var lexical = {indented: -2, column: 0, type: "block", align: false};
  var column = 0;
  var indented = 0;

  var parser = {next: next, copy: copy};

  function next(){
    var token = tokens.next();
    if (token.type == "whitespace" && column == 0)
      indented = token.value.length;
    column += token.value.length;
    if (token.type == "newline"){
      while(cc[cc.length - 1].lex)
        cc.pop()();
      indented = column = 0;
      if (!("align" in lexical))
        lexical.align = false;
      token.indent = currentIndentation();
    }
    if (token.type == "whitespace" || token.type == "newline" || token.type == "comment")
      return token;
    if (!("align" in lexical))
      lexical.align = true;

    while(true){
      consume = markdef = false;
      cc.pop()(token.type, token.name);
      if (consume){
        if (token.type == "variable") {
          if (markdef)
            token.style = "variabledef";
          else if (inScope(token.name))
            token.style = "localvariable";
        }
        return token;
      }
    }
  }
  function copy(){
    var _context = context, _lexical = lexical, _cc = copyArray(cc), _regexp = tokens.regexp, _comment = tokens.inComment;

    return function(newTokens){
      context = _context;
      lexical = _lexical;
      cc = copyArray(_cc);
      column = indented = 0;
      tokens = newTokens;
      tokens.regexp = _regexp;
      tokens.inComment = _comment;
      return parser;
    };
  }

  function push(fs){
    for (var i = fs.length - 1; i >= 0; i--)
      cc.push(fs[i]);
  }
  function cont(){
    push(arguments);
    consume = true;
  }
  function pass(){
    push(arguments);
    consume = false;
  }

  function pushcontext(){
    context = {prev: context, vars: {}};
  }
  function popcontext(){
    context = context.prev;
  }
  function register(varname){
    if (context){
      markdef = true;
      context.vars[varname] = true;
    }
  }
  function inScope(varname){
    var cursor = context;
    while (cursor) {
      if (cursor.vars[varname])
        return true;
      cursor = cursor.prev;
    }
    return false;
  }

  function pushlex(type){
    var result = function(){
      lexical = {prev: lexical, indented: indented, column: column, type: type};
    };
    result.lex = true;
    return result;
  }
  function poplex(){
    lexical = lexical.prev;
  }
  poplex.lex = true;
  function currentIndentation(){
    if (lexical.type == "stat")
      return lexical.indented + 2;
    else if (lexical.align)
      return lexical.column + 1;
    else
      return lexical.indented + 2;
  }

  function expect(wanted){
    return function(type){
      if (type == wanted) cont();
      else cont(arguments.callee);
    };
  }

  function statements(type){
    return pass(statement, statements);
  }
  function statement(type){
    if (type == "var") cont(pushlex("stat"), vardef1, expect(";"), poplex);
    else if (type == "keyword a") cont(pushlex("stat"), expression, statement, poplex);
    else if (type == "keyword b") cont(pushlex("stat"), statement, poplex);
    else if (type == "{") cont(pushlex("block"), block, poplex);
    else if (type == "function") cont(functiondef);
    else pass(pushlex("stat"), expression, expect(";"), poplex);
  }
  function expression(type){
    if (type in atomicTypes) cont(maybeoperator);
    else if (type == "function") cont(functiondef);
    else if (type == "keyword c") cont(expression);
    else if (type == "(") cont(pushlex("block"), expression, expect(")"), poplex);
    else if (type == "operator") cont(expression);
  }
  function maybeoperator(type){
    if (type == "operator") cont(expression);
    else if (type == "(") {cont(pushlex("block"), expression, commaseparated, expect(")"), poplex)};
  }
  function commaseparated(type){
    if (type == ",") cont(expression, commaseparated);
  }
  function block(type){
    if (type == "}") cont();
    else pass(statement, block);
  }
  function vardef1(type, value){
    if (type == "variable"){register(value); cont(vardef2);}
    else cont();
  }
  function vardef2(type, value){
    if (value == "=") cont(expression, vardef2);
    else if (type == ",") cont(vardef1);
  }
  function functiondef(type, value){
    if (type == "variable"){register(value); cont(functiondef);}
    else if (type == "(") cont(pushcontext, arglist1, expect(")"), statement, popcontext);
  }
  function arglist1(type, value){
    if (type == "variable"){register(value); cont(arglist2);}
  }
  function arglist2(type){
    if (type == ",") cont(arglist1);
  }

  return parser;
}

function JSEditor(place, width, height, content) {
  this.frame = createDOM("IFRAME", {"style": "border: 0; width: " + width + "px; height: " + height + "px;"});
  place(this.frame);
  this.win = this.frame.contentWindow;
  this.doc = this.win.document;
  this.doc.designMode = "on";
  this.doc.open();
  this.doc.write("<html><head><link rel=\"stylesheet\" type=\"text/css\" href=\"highlight.css\"/></head>" +
                 "<body class=\"editbox\" spellcheck=\"false\"></body></html>");
  this.doc.close();

  this.dirty = [];

  if (document.selection) // better check?
    this.init(content);
  else
    connect(this.frame, "onload", bind(function(){disconnectAll(this.frame, "onload"); this.init(content);}, this));
}

JSEditor.prototype = {
  linesPerShot: 10,
  shotDelay: 300,

  init: function (code) {
    this.container = this.doc.body;
    if (code)
      this.importCode(code);
    connect(this.doc, "onmouseup", bind(this.markCursorDirty, this));
    if (document.selection)
      connect(this.doc, "onkeydown", bind(this.insertEnter, this));
    connect(this.doc, "onkeyup", bind(this.handleKey, this));
  },

  importCode: function(code) {
    code = code.replace(/[ \t]/g, nbsp);
    replaceChildNodes(this.container, this.doc.createTextNode(code));
    exhaust(traverseDOM(this.container.firstChild));
    if (this.container.firstChild){
      this.addDirtyNode(this.container.firstChild);
      this.scheduleHighlight();
    }
  },

  insertEnter: function(event) {
    if (event.key().string == "KEY_ENTER"){
      insertNewlineAtCursor(this.win);
      var cur = new Cursor(this.container);
      this.indentAtCursor(cur);
      event.stop();
    }
  },

  handleKey: function(event) {
    if (event.key().string == "KEY_ENTER")
      this.indentAtCursor(new Cursor(this.container));
    else
      this.markCursorDirty();
  },

  highlightAtCursor: function (cursor) {
    if (cursor.valid && this.container.lastChild) {
      var node = cursor.after ? cursor.after.previousSibling : this.container.lastChild;
      if (node.nodeType != 3)
        node.dirty = true;
      var sel = markSelection(this.win);
      this.highlight(node, true);
      selectMarked(sel);
      cursor = new Cursor(this.container);
    }
    return cursor;
  },

  indentAtCursor: function(cursor) {
    cursor = this.highlightAtCursor(cursor);
    if (!cursor.valid)
      return;

    var start = cursor.startOfLine();
    var whiteSpace = start ? start.nextSibling : this.container.firstChild;
    if (whiteSpace && !hasClass(whiteSpace, "whitespace"))
      whiteSpace = null;

    var indentDiff = (start ? start.indent : 0) - (whiteSpace ? whiteSpace.text.length : 0);
    if (indentDiff < 0) {
      whiteSpace.text.slice(-indentDiff);
      whiteSpace.firstChild.nodeValue = whiteSpace.text;
    }
    else if (indentDiff > 0) {
      if (whiteSpace) {
        whiteSpace.text += repeatString(nbsp, indentDiff);
        whiteSpace.firstChild.nodeValue = whiteSpace.text;
      }
      else {
        var newNode = this.doc.createTextNode(repeatString(nbsp, indentDiff));
        if (start)
          insertAfter(newNode, start);
        else
          insertAtStart(newNode, this.containter);
      }
    }
    cursor.focus();
  },

  highlight: highlight,

  markCursorDirty: function() {
    var cursor = new Cursor(this.container);
    if (cursor.valid && this.container.lastChild) {
      this.scheduleHighlight();
      this.addDirtyNode(cursor.after ? cursor.after.previousSibling : this.container.lastChild);
    }
  },

  addDirtyNode: function(node) {
    if (!member(this.dirty, node)){
      if (node.nodeType != 3)
        node.dirty = true;
      this.dirty.push(node);
    }
  },

  scheduleHighlight: function() {
    clearTimeout(this.highlightTimeout);
    this.highlightTimeout = setTimeout(bind(this.highlightDirty, this, this.linesPerShot), this.shotDelay);
  },

  getDirtyNode: function() {
    while (this.dirty.length > 0) {
      var found = this.dirty.pop();
      if ((found.dirty || found.nodeType == 3) && found.parentNode)
        return found;
    }
    return null;
  },

  highlightDirty: function(lines) {
    var sel = markSelection(this.win);
    var start;
    while (lines > 0 && (start = this.getDirtyNode())){
      var result = this.highlight(start, true, lines);
      if (result) {
        lines = result.left;
        if (result.node && result.dirty)
          this.addDirtyNode(result.node);
      }
    }
    selectMarked(sel);
    if (start)
      this.scheduleHighlight();
  }
}

function highlight(from, onlyDirtyLines, lines){
  var doc = this.doc;
  var body = doc.body;
  if (!body.firstChild)
    return;
  while (from && !from.parserFromHere)
    from = from.previousSibling;
  if (from && !from.nextSibling)
    return;

  function correctPart(token, part){
    return !part.reduced && part.text == token.value && hasClass(part, token.style);
  }
  function shortenPart(part, minus){
    part.text = part.text.substring(minus);
    part.reduced = true;
  }
  function tokenPart(token){
    var part = withDocument(doc, partial(SPAN, {"class": "part " + token.style}, token.value));
    part.text = token.value;
    return part;
  }

  var parsed = from ? from.parserFromHere(tokenize(stringCombiner(traverseDOM(from.nextSibling))))
                    : parse(tokenize(stringCombiner(traverseDOM(body.firstChild))));

  var parts = {
    current: null,
    forward: false,
    get: function(){
      if (!this.current){
        this.current = from ? from.nextSibling : body.firstChild;
      }
      else if (this.forward){
        this.forward = false;
        this.current = this.current.nextSibling;
      }
      return this.current;
    },
    next: function(){
      if (this.forward)
        this.get();
      this.forward = true;
    },
    remove: function(){
      this.current = this.get().previousSibling;
      body.removeChild(this.current.nextSibling);
      this.forward = true;
    }
  };

  var lineDirty = false;

  forEach(parsed, function(token){
    var part = parts.get();
    if (token.type == "newline"){
      if (part.nodeName != "BR")
        debugger;//throw "Parser out of sync. Expected BR.";
      part.parserFromHere = parsed.copy();
      part.indent = token.indent;
      if (part.dirty)
        lineDirty = true;
      part.dirty = false;
      if ((lines !== undefined && --lines <= 0) ||
          (onlyDirtyLines && !lineDirty))
        throw StopIteration;
      lineDirty = false;
      parts.next();
    }
    else {
      if (part.nodeName != "SPAN")
        debugger;//throw "Parser out of sync. Expected SPAN.";
      if (part.dirty)
        lineDirty = true;

      if (correctPart(token, part)){
        part.dirty = false;
        parts.next();
      }
      else {
        lineDirty = true;
        var newPart = tokenPart(token);
        body.insertBefore(newPart, part);
        var tokensize = token.value.length;
        while (tokensize > 0) {
          part = parts.get();
          var partsize = part.text.length;
          replaceSelection(part.firstChild, newPart.firstChild, tokensize);
          if (partsize > tokensize){
            shortenPart(part, tokensize);
            tokensize = 0;
          }
          else {
            tokensize -= partsize;
            parts.remove();
          }
        }
      }
    }
  });

  return {left: lines,
          node: parts.get(),
          dirty: lineDirty};
}
