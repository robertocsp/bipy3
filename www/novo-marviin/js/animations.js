(function($) {

"use strict";

$(document).ready(function() {

	$('.intro-product-media, .feature-block, .feature-media, .feature').css('opacity', 0);


	$(window).load( function() {
		setTimeout(function(){	

			/* ================================================	
				INTRO
			================================================ */
			$('.intro-product-media').animo( { animation: 'fadeInUp', duration: 1.0, keep: true } );



			/* ================================================
				FEATURES BLOCK
			================================================ */
			$('.features-blocks').waypoint(function(){
				$('.feature-block').each(function(index){
						$(this).css({
							'animation-delay' : (index * 0.3) + "s",
							'-webkit-animation-delay' : (index * 0.3) + "s",
							'-moz-animation-delay' : (index * 0.3) + "s",
							'-ms-animation-delay' : (index * 0.3) + "s",
							'-o-animation-delay' : (index * 0.3) + "s"
						});
				});
				$('.feature-block').animo( { animation: 'fadeInUp', duration: 0.7, keep: true } );
			});



			/* ================================================
				FEATURES MEDIA
			================================================ */
			$('.features-media').each(function(index){
				$('.features-media').eq(index).waypoint(function(){
					$('.feature-media').eq(index).animo( { animation: 'fadeInUp', duration: 0.7, keep: true } );
				}, { offset: 100 });
			});



			/* ================================================
				FEATURES OVERVIEW
			================================================ */
			$('.features-overview').waypoint(function(){
				$('.feature').each(function(index){
						$(this).css({
							'animation-delay' : (index * 0.3) + "s",
							'-webkit-animation-delay' : (index * 0.3) + "s",
							'-moz-animation-delay' : (index * 0.3) + "s",
							'-ms-animation-delay' : (index * 0.3) + "s",
							'-o-animation-delay' : (index * 0.3) + "s"
						});
				});
				$('.feature').animo( { animation: 'fadeInLeft', duration: 0.7, keep: true } );
			}, { offset: 200 });


			/* ================================================
				DOWNLOAD
			================================================ */
			$('.download-product').waypoint(function(){
				$('.download-product .logo').animo( { animation: 'tada', duration: 0.7, keep: true } );
			}, { offset: 200 });


		}, 300); // setTimeout()
	}); // $(window).load( function() {


}); // $(document).ready(function() {
}(jQuery)); // (function($) {