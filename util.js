function isString(x){return typeof(x) == "string";}

registerIteratorFactory("string", isString, function (string){
  var pos = 0;
  return {next: function() {
    if (pos < string.length) return string.charAt(pos++);
    else throw StopIteration;
  }};
});

function nextOr(iter, alternative){
  try {
    return iter.next();
  }
  catch (e) {
    if (e != StopIteration)
      throw e;
    else return alternative;
  }
}

function tryNext(iter, regular, alternative){
  try {
    return regular(iter.next());
  }
  catch (e) {
    if (e != StopIteration)
      throw e;
    else if (alternative)
      return alternative();
  }
}

function constantly(value){
  return function(){return value;}
}

function iconcat(iterators){
  var current = iter([]);
  function next(){
    return tryNext(
      current,
      operator.identity,
      function(){
        current = iter(iterators.next());
        return next();
      });
  }
  return {next: next};
}

function peekIter(iter, eofMarker){
  var peeked = false, peekValue = null;
  return {
    peek: function(){
      if (!peeked){
        peeked = true;
        peekValue = nextOr(iter, eofMarker);
      }
      return peekValue;
    },
    next: function(){
      if (peeked){
        if (peekValue === eofMarker)
          throw StopIteration;
        peeked = false;
        return peekValue;
      }
      else{
        return iter.next();
      }
    }
  };
}

function setObject(){
  var obj = {};
  forEach(arguments, function(value){
    obj[value] = true;
  });
  return obj;
}

function matcher(regexp){
  return function(value){return regexp.test(value);};
}
