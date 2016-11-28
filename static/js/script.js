$(document).ready(function() {
  $("#date").click(function() {
    var start_date = $("[name='start_date']").val()
    var end_date = $("[name='end_date']").val()
    var start_time = $("[name='start_time']").val()
    var end_time = $("[name='end_time']").val()
    $.getJSON( "/_setrange", { start_date: start_date, end_date: end_date, start_time: start_time, end_time: end_time },
      function(data) {
        //code goes here
      }
    );
  });
});