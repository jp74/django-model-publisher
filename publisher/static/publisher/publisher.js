var $ = django.jQuery;
$(function() {
  $('input:checkbox.publish-checkbox').change(function() {
    if ($(this).is(':checked')) {
      var url = $(this).attr('data-publish');
    } else {
      var url = $(this).attr('data-unpublish');
    }
    $.get(url, function(data) {
      if (data.success) {
        $('.published-icon').find('img').toggle();
      }
    });
  });
});
