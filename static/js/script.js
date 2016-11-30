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
    var checked = [];
    $("input:checkbox[name='calendar']:checked").each(function(){
      checked.push($(this).val());
    });
    if (checked.length == 0) {
      alert("Please select a calendar to pull events from!");
    } else {
      var checked_csv = "";
      for (var i=0;i<checked.length;i++) {
        checked_csv += String(checked[i]);
        if (i != (checked.length-1)) {
            checked_csv += ",";
        }
      }
      $("#calendar_pick").fadeOut();
      $.getJSON( "/_setcalendar", { selected_calendars: checked_csv },
        function(data) {
          for (var key in data.result) {
            $("[name='conflicts']").append('<input type="checkbox" name="conflict" value='+data.result[key]['id']+' checked> '+data.result[key]['summary']+'<br />');
          }
          setTimeout(function() {
            $("#conflict_pick").fadeIn()
          }, 400);
        }
      );
    }
  });


});