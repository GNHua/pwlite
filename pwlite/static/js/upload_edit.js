// List of pending files to handle when the Upload button is finally clicked.
let PENDING_FILES  = [];
let upload_from_upload_page = $('#dropbox').length > 0;

$(document).ready(function() {
  // Set up the handler for the file input box.
  $('#file-picker').on('change', function() {
    addFiles(this.files);
    doUpload();
  });
});

function addFiles(files) {
  // Add them to the pending files list.
  for (let i = 0; i < files.length; i++) {
    PENDING_FILES.push(files[i]);
  }
}

function doUpload() {
  // Collect the form data.
  let fd = new FormData();

  // Attach the files.
  for (let i = 0; i < PENDING_FILES.length; i++) {
    // Collect the other form data.
    fd.append('wiki_file', PENDING_FILES[i]);
  }

  fd.append('wiki_page_id', wiki_page_id);
  if (upload_from_upload_page) {
    let placeholder = 1;
    fd.append('upload_page', placeholder);
  }

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
    url: '/' + wiki_group + '/handle-upload',
    method: 'POST',
    contentType: false,
    processData: false,
    cache: false,
    data: fd,
    success: function(data) {
      PENDING_FILES.splice(0, PENDING_FILES.length);
      editor.replaceRange(data, CodeMirror.Pos(editor.lastLine()))
    }
  });
}
