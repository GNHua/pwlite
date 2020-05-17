// List of pending files to handle when the Upload button is finally clicked.
let PENDING_FILES  = [];
let upload_from_upload_page = $('#dropbox').length > 0;

$(document).ready(function() {
  // Set up the handler for the file input box.
  $('#file-picker').on('change', function() {
    addFiles(this.files);
  });

  // Set up the drag/drop zone.
  initDropbox();

  // Handle the submit button.
  $('#upload-button').on('click', function(e) {
    // If the user has JS disabled, none of this code is running but the
    // file multi-upload input box should still work. In this case they'll
    // just POST to the upload endpoint directly. However, with JS we'll do
    // the POST using ajax and then redirect them ourself when done.
    e.preventDefault();
    if (PENDING_FILES.length == 0) {
      window.close();
    }
    doUpload();
  });
});

function initDropbox() {
  let $dropbox = $('#dropbox');

  // On drag enter...
  $dropbox.on('dragenter', function(e) {
    e.stopPropagation();
    e.preventDefault();
    $(this).addClass('active');
  });

  $dropbox.on('dragleave', function(e) {
    e.stopPropagation();
    e.preventDefault();
    $(this).removeClass('active');
  });

  // On drag over...
  $dropbox.on('dragover', function(e) {
    e.stopPropagation();
    e.preventDefault();
  });

  // On drop...
  $dropbox.on('drop', function(e) {
    e.preventDefault();
    $(this).removeClass('active');

    // Get the files.
    let files = e.originalEvent.dataTransfer.files;
    addFiles(files);
  });

  // If the files are dropped outside of the drop zone, the browser will
  // redirect to show the files in the window. To avoid that we can prevent
  // the 'drop' event on the document.
  function stopDefault(e) {
    e.stopPropagation();
    e.preventDefault();
  }
  $(document).on('dragenter', stopDefault);
  $(document).on('dragover', stopDefault);
  $(document).on('drop', stopDefault);
}

function addFiles(files) {
  let $selected = $('#selected-files');

  // Add them to the pending files list.
  for (let i = 0; i < files.length; i++) {
    PENDING_FILES.push(files[i]);

    // Show added files on upload page
    let li_file = $('<li/>', {
      class: 'list-group-item d-flex justify-content-between align-items-center',
      text: files[i].name}).appendTo($selected);
    let del_file = $('<button/>', {
      type: 'button',
      class: 'ml-auto btn btn-sm btn-danger',
      html: '&times;'
    }).appendTo(li_file);
    del_file.on('click', function() {
      PENDING_FILES.splice($(this).parent().index(), 1);
      $(this).parent().remove();
      $('#file-number').text(get_file_str());
    });
  }

  let get_file_str = function() {
    let file_str = PENDING_FILES.length > 1 ? ' files':' file';
    return PENDING_FILES.length + file_str + ' selected';
  }
  $('#file-number').text(get_file_str());
}

function doUpload() {
  $('#progress').show();
  let $progressBar   = $('#progress-bar');
  let $completion = $('#completion');

  // Gray out the form.
  $(':input').attr('disabled', 'disabled');

  // Initialize the progress bar.
  $progressBar.css({'width': '0%'});

  // Collect the form data.
  // fd = collectFormData();
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
      if (xhrobj.upload) {
        xhrobj.upload.addEventListener('progress', function(event) {
          let percent = 0;
          let position = event.loaded || event.position;
          let total    = event.total;
          if (event.lengthComputable) {
            percent = Math.ceil(position / total * 100);
          }

          // Set the progress bar.
          $progressBar.css({'width': percent + '%'});
          $completion.text(percent + '%');
        }, false)
      }
      return xhrobj;
    },
    url: '/' + wiki_group + '/handle-upload',
    method: 'POST',
    contentType: false,
    processData: false,
    cache: false,
    data: fd,
    success: function(data) {
      $progressBar.css({'width': '100%'});
      opener.location.reload();
      window.close();
    }
  });
}
