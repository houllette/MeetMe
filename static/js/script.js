$("#date").click(function() {
  var txt = "something";
  $.getJSON( "/_example", { text: txt },
    function(data) {
      //code goes here
    }
  );
});