/* =================================
   LOADER                     
=================================== */
// makes sure the whole site is loaded
jQuery(window).load(function() {
        // will first fade out the loading animation
	jQuery(".status").fadeOut();
        // will fade out the whole DIV that covers the website.
	jQuery(".preloader").delay(1000).fadeOut("slow");
})

/* =================================
===  RESPONSIVE VIDEO           ====
=================================== */

$(".video-container").fitVids();

function mailchimpCallback(resp) {
     if (resp.result === 'success') {
        $('.subscription-success').html('<i class="icon_check_alt2"></i><br/>' + resp.msg).fadeIn(1000);
        $('.subscription-error').fadeOut(500);
        
    } else if(resp.result === 'error') {
        $('.subscription-error').html('<i class="icon_close_alt2"></i><br/>' + resp.msg).fadeIn(1000);
    }  
}

/* =================================
===  STICKY NAV                 ====
=================================== */

$(document).ready(function() {
  $('.main-navigation').onePageNav({
    scrollThreshold: 0.2, // Adjust if Navigation highlights too early or too late
    filter: ':not(.external)',
    changeHash: true
  });
  
});


/* COLLAPSE NAVIGATION ON MOBILE AFTER CLICKING ON LINK - ADDED ON V1.5*/

if (matchMedia('(max-width: 480px)').matches) {
    $('.main-navigation a').on('click', function () {
        $(".navbar-toggle").click();
    });
}

/* =================================
===  DOWNLOAD BUTTON CLICK SCROLL ==
=================================== */
jQuery(function( $ ){
	$('#download-button').localScroll({
		duration:1000
	});
});


/* =================================
===  FULL SCREEN HEADER         ====
=================================== */
function alturaMaxima() {
  var altura = $(window).height();
  $(".full-screen").css('min-height',altura); 
  
}

$(document).ready(function() {
  alturaMaxima();
  $(window).bind('resize', alturaMaxima);
});


/* =================================
===  SMOOTH SCROLL             ====
=================================== */
var scrollAnimationTime = 1200,
    scrollAnimation = 'easeInOutExpo';
$('a.scrollto').bind('click.smoothscroll', function (event) {
    event.preventDefault();
    var target = this.hash;
    $('html, body').stop().animate({
        'scrollTop': $(target).offset().top
    }, scrollAnimationTime, scrollAnimation, function () {
        window.location.hash = target;
    });
});


/* =================================
===  WOW ANIMATION             ====
=================================== */
wow = new WOW(
  {
    mobile: false
  });
wow.init();


/* =================================
===  OWL CROUSEL               ====
=================================== */
$(document).ready(function () {

    $("#feedbacks").owlCarousel({

        navigation: false, // Show next and prev buttons
        slideSpeed: 800,
        paginationSpeed: 400,
        autoPlay: 5000,
        singleItem: true
    });

    var owl = $("#screenshots");

    owl.owlCarousel({
        items: 4, //10 items above 1000px browser width
        itemsDesktop: [1000, 4], //5 items between 1000px and 901px
        itemsDesktopSmall: [900, 2], // betweem 900px and 601px
        itemsTablet: [600, 1], //2 items between 600 and 0
        itemsMobile: false // itemsMobile disabled - inherit from itemsTablet option
    });
	
	$("#bg-page").height($(document).height());
	
	$("#fecha-video").click(function(){
		$("#video").hide("slow");
	});

	$("#open-video").click(function(){
	  $("#video").show("slow");
	});

});


/* =================================
===  Nivo Lightbox              ====
=================================== */
$(document).ready(function () {

    $('#screenshots a').nivoLightbox({
        effect: 'fadeScale',
    });

});

/* =================================
===  EXPAND COLLAPSE            ====
=================================== */
/*
jQuery(function( $ ){
    $('.expand-form').simpleexpand({
        'defaultTarget': '.expanded-contact-form'
    });
});
*/

/* =================================
===  STELLAR                    ====
=================================== */
$(window).stellar({ 
horizontalScrolling: false 
});


/* =================================
===  Bootstrap Internet Explorer 10 in Windows 8 and Windows Phone 8 FIX
=================================== */
if (navigator.userAgent.match(/IEMobile\/10\.0/)) {
  var msViewportStyle = document.createElement('style')
  msViewportStyle.appendChild(
    document.createTextNode(
      '@-ms-viewport{width:auto!important}'
    )
  )
  document.querySelector('head').appendChild(msViewportStyle)
}

jQuery(function( $ ){
    var SPMaskBehavior = function (val) {
      return val.replace(/\D/g, '').length === 11 ? '(00) 00000-0000' : '(00) 0000-00009';
    },
    spOptions = {
      onKeyPress: function(val, e, field, options) {
          field.mask(SPMaskBehavior.apply({}, arguments), options);
      }
    };

    $('.telefone-estabelecimento').mask(SPMaskBehavior, spOptions);
    $('.cep-estabelecimento').mask('00000-000');

    var setaParaCima = function () {
        $('.form-estabelecimentos i.fa-arrow-up').unbind('click');
        $('.form-estabelecimentos i.fa-arrow-down').unbind('click');
        var $thisLabel = $(this).siblings('input');
        var indice = parseInt($thisLabel.val());
        if (indice > 1)
        {
            var $label = $(this).closest('label');
            var $prevLabel = $label.prev('label');
            $prevLabel.find('input').val(indice);
            $thisLabel.val(indice-1);
            $prevLabel.before($label);
        }
        $('.form-estabelecimentos i.fa-arrow-up').bind('click', setaParaCima);
        $('.form-estabelecimentos i.fa-arrow-down').bind('click', setaParaBaixo);
    };
    $('.form-estabelecimentos i.fa-arrow-up').bind('click', setaParaCima);

    var setaParaBaixo = function () {
        $('.form-estabelecimentos i.fa-arrow-up').unbind('click');
        $('.form-estabelecimentos i.fa-arrow-down').unbind('click');
        var $thisLabel = $(this).siblings('input');
        var indice = parseInt($thisLabel.val());
        if (indice < 10)
        {
            var $label = $(this).closest('label');
            var $nextLabel = $label.next('label');
            $nextLabel.find('input').val(indice);
            $thisLabel.val(indice+1);
            $nextLabel.after($label);
        }
        $('.form-estabelecimentos i.fa-arrow-up').bind('click', setaParaCima);
        $('.form-estabelecimentos i.fa-arrow-down').bind('click', setaParaBaixo);
    };
    $('.form-estabelecimentos i.fa-arrow-down').bind('click', setaParaBaixo);
});