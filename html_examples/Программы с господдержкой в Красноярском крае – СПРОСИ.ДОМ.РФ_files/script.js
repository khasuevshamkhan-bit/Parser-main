$(document).ready(function() {
  $('.js--ctlg-srt').on( 'click', '.js-btn', function( event ) {
    $(location).attr('href', $(this).attr('data-href'));
  });
});
