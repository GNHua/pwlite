let selected_wiki_file;

// Trigger action when the contexmenu is about to be shown
$('.wiki-file').bind("contextmenu", function (event) {

  // Avoid the real one
  event.preventDefault();

  // Show contextmenu
  $(".custom-menu").finish().toggle(100).
    // In the right position (the mouse)
    css({
      top: event.pageY + "px",
      left: event.pageX + "px"
    });
  
  selected_wiki_file = $(this)[0];
});


// If the document is clicked somewhere
$(document).bind("mousedown", function (e) {

  // If the clicked element is not the menu
  if (!$(e.target).parents(".custom-menu").length > 0) {

    // Hide it
    $(".custom-menu").hide(100);
    // selected_wiki_file = null;
  }
});


// If the menu element is clicked
$(".custom-menu li").click(function(){

  // This is the triggered action name
  switch($(this).attr("data-action")) {

    // A case for each action. Your actions here
    case "Download": selected_wiki_file.click(); break;
    case "Replace": document.getElementById('file-picker').click(); break;
  }

  // Hide it AFTER the action was triggered
  $(".custom-menu").hide(100);
});


$(document).ready(function() {
  // Set up the handler for the file input box.
  $('#file-picker').on('change', function() {
    doUpload(this.files[0]);
  });
});

function doUpload(file) {
  // Collect the form data.
  let fd = new FormData();
  fd.append('wiki_file', file);

  let str = selected_wiki_file.pathname.split('/');
  fd.append('wiki_file_id', str[str.length-1]);

  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader('X-CSRFToken', $('meta[name=csrf-token]').attr('content'));
      }
    }
  })

  let xhr = $.ajax({
    xhr: function() {
      let xhrobj = $.ajaxSettings.xhr();
      return xhrobj;
    },
    url: '/' + wiki_group + '/replace-file',
    method: 'POST',
    contentType: false,
    processData: false,
    cache: false,
    data: fd,
    success: function(data) {
      location.reload();
    }
  });
}
