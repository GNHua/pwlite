$('#inputDateFrom').datepicker({
  format: 'mm/dd/yyyy',
  todayHighlight: true
});

$('#inputDateTo').datepicker({
  format: 'mm/dd/yyyy',
  todayHighlight: true
});

$('#inputDateFrom').datepicker()
  .on('changeDate', function(e) {
    let dateFrom = $('#inputDateFrom').datepicker('getDate');
    let dateTo = $('#inputDateTo').datepicker('getDate');
    if (dateTo && +dateFrom > +dateTo) {
      $('#inputDateTo').datepicker('setDate', dateFrom);
    }
    $('#inputDateTo').datepicker('setStartDate', dateFrom);
  });

$('#inputDateTo').datepicker()
  .on('changeDate', function(e) {
    let dateFrom = $('#inputDateFrom').datepicker('getDate');
    let dateTo = $('#inputDateTo').datepicker('getDate');
    if (dateFrom && +dateFrom > +dateTo) {
      $('#inputDateFrom').datepicker('setDate', dateTo);
    }
    $('#inputDateFrom').datepicker('setEndDate', dateTo);
  });