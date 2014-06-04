$(function() {
    $('.col-published.publisher input[type="checkbox"]').change(function() {
        if ($(this).attr('checked')) {
            var url = $(this).data('publish');
        }
        else {
            var url = $(this).data('unpublish');
        }

        $.get(url, function(json) { });
    })
})