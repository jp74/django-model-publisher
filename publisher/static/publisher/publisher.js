var $ = django.jQuery;
$(function() {
    $('input:checkbox.publish-checkbox').change(function() {
        if ($(this).is(':checked')) {
            var url = $(this).data('publish');
        }
        else {
            var url = $(this).data('unpublish');
        }
        $.get(url, function(json) { });
    })
})
