var base_url = 'https://sistema.marviin.com.br';
//var base_url = 'http://localhost:8888';

$(document).ready(function() {

  var win = $(window);

  $(window).load(function() {
    $(".preloader").delay(1000).fadeOut("slow");
    $('body').css('overflow', 'auto');
  });


  /* ================================================
     NAVIGATION
  ================================================ */
  /* -----------------------------
     Show/Hide Nav on scroll
  ----------------------------- */
  // set defaults
  /*
  var nav = $('.pagina-inicial #main-nav'),
      navHeight = nav.outerHeight(),

      lastScrollTop = 0;

  // hide menu on load
  nav.css('top', navHeight * -1);
*/

  // get new height value when resizing for smaller screens
  win.resize(function(){
    if (matchMedia('(max-width: 992px)').matches) {
      navHeight = nav.outerHeight();
    }
  });

  // event
  win.scroll(function(){
    // do not scroll mobile menu up when opened 
    if ( ! ( $('.navbar-collapse').hasClass('in') ) ) {
      // if mobile menu not opened and not on small screens
      var currentScollTop = $(this).scrollTop();
      if (currentScollTop < lastScrollTop || win.scrollTop() < 800) {
        // downscroll code
        nav.css('top', navHeight * -1);
      } else {
        // upscroll code
        nav.css('top', 0);
      }
      lastScrollTop = currentScollTop;
    }
  });

  
  $('#main-nav-ul a').click(function(){
    if (matchMedia('(max-width: 768px)').matches) {
      $('.navbar-toggle').click();
    }
  });

  $('body').localScroll({
     target:'body',
     duration: 750
  });


  /* -----------------------------
     ScrollTo & LocalScroll
  ----------------------------- */
  $('#main-nav-ul').onePageNav({
      currentClass: 'current',
      changeHash: false,
      scrollSpeed: 750,
      scrollThreshold: 0.5,
  });

  /* -----------------------------
     Owl Carousel
  ----------------------------- */
  $('.companies-logo-slider').owlCarousel({
    autoplay: true,
    slideBy: 'page',

    responsive: {
      0: { items: 2 },
      768: { items: 4 }
    }
  });


  $('.testimonials-slider').owlCarousel({
    autoplay: true,
    autoplayHoverPause: true,
    autoplaySpeed: 1000,
    dotsSpeed: 1000,

    responsive: {
      0: { items: 1 }
    }
  });

  $('.screens-gallery-slider').owlCarousel({
    autoplay: true,
    autoplayHoverPause: true,
    margin: 20,
	nav: false,
	loop: true,

    responsive: {
      0: { items: 1 },
      768: { items: 1 },
    }
  });



  /* -----------------------------
     Magnific Popup Lightbox
  ----------------------------- */
  $('.intro-product-media, .screens-gallery-slider, .feature-media.image').magnificPopup({
    delegate: 'a',
    type: 'image'
  });

  
  $('.feature-media.video a, .watch-video').magnificPopup({
    disableOn: 700,
    type: 'iframe',
    removalDelay: 160,
    preloader: false,

    fixedContentPos: false
  });


  /* -----------------------------
     Stellar Parallax
  ----------------------------- */
  win.stellar({
    horizontalScrolling: false,
    verticalOffset: 0
  });
  // fix for resizing bg pos issues
  win.resize(function() {
      $(this).stellar('refresh');
  });
  // fix random pos bug
  setTimeout(function(){
    win.stellar('refresh');
  }, 2000);


   $('.video').fitVids();

});

//Envio de formulário
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

    //Envio
    function montaDados(jsonArray)
    {
        var json_envio = {};
        for (var i in jsonArray)
        {
            if(jsonArray[i].name.startsWith('campo'))
            {
                if(json_envio['ordem_campos']===undefined)
                    json_envio['ordem_campos'] = [];
                json_envio['ordem_campos'].push($('#'+jsonArray[i].name).parent().text());
            }
            else
            {
                json_envio[jsonArray[i].name] = jsonArray[i].value;
            }
        }
        return json_envio;
    }

    function envia_form(form, service, form_function) {
        $form_this = $('.' + form);
        if($form_this[0].checkValidity()) {
            $form_this.unbind('submit');
            $('#carregando').show();

            var dados_envio = montaDados($form_this.serializeArray());

            $.post(base_url + '/marviin/api/rest/' + service,
                     {formulario_dados: JSON.stringify(dados_envio)},
                     function(data) {
                       console.log(data);
                     },
                     'json'
            )
            .fail(function(data) {
                console.log(data);
            })
            .always(function() {
                $('#carregando').hide();
                $form_this[0].reset();
                $form_this.bind('submit', form_function);
            });
        }
        else
        {
            console.log("invalid form");
        }
    }

    var form_estabelecimentos_function = function(){
        envia_form('form-estabelecimentos', 'pesquisa_estabelecimento', form_estabelecimentos_function);
    };
    $('.form-estabelecimentos').bind('submit', form_estabelecimentos_function);

    var form_indicacao_usuario_function = function(){
        envia_form('form-indicacao-usuario', 'indicacao_usuario', form_indicacao_usuario_function);
    };
    $('.form-indicacao-usuario').bind('submit', form_indicacao_usuario_function);

    var form_fale_conosco_function = function(){
        envia_form('form-faleconosco', 'fale_conosco', form_fale_conosco_function);
    };
    $('.form-faleconosco').bind('submit', form_fale_conosco_function);
});