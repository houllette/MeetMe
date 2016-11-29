$(document).ready(function() {

  $("#receiver_view").hide();
  $("#calendar_pick").hide();
  $("#conflict_pick").hide();

  $("#date").click(function() {
    var start_date = $("[name='start_date']").val();
    var end_date = $("[name='end_date']").val();
    var start_time = $("[name='start_time']").val();
    var end_time = $("[name='end_time']").val();
    $("#creator_view").fadeOut();
    $.getJSON( "/_setrange", { start_date: start_date, end_date: end_date, start_time: start_time, end_time: end_time },
      function(data) {
        for (var key in data.result) {
          $("[name='calendars']").append('<input type="checkbox" name="calendar" value='+data.result[key]['id']+'> '+data.result[key]['summary']+'<br />');
        }
        setTimeout(function() {
          $("#calendar_pick").fadeIn()
        }, 400);
      }
    );
  });

  $("#calendars").click(function() {
    var txt = "test";
    alert(txt);
    $("calendar_pick").fadeOut();
    /*
    $.getJSON( "/_setrange", { text: txt },
      function(data) {

        $("conflict_pick").fadeIn();
      }
    );
    */
  });


});