function setup_cad_endereco(psid)
{
    $('form#form-cadend').validate({
        rules: {
            cep: { required: true },
            endereco: { required: true },
            complemento: { required: true },
            bairro: { required: true },
            cidade: { required: true },
            estado: { required: true },
        },
        submitHandler: function(form) {
            if(psid)
                form.action += '&psid=' + psid;
            form.submit();
        },
        invalidHandler: function(event, validator) {
            $(this).removeClass('nosubmit');
        },
        onfocusout: false,
        onkeyup: false,
        onclick: false
    });

    $(".btn-add-bloco-end").click(function(){
        numeroEndereco = Number($(".blocos-endereco .bloco-endereco:last-child .num-endereco").text()) + 1;

        $(".blocos-endereco").append("<div class='bloco-endereco'> "+
            "<label class='titulo-label'>Endereço <span class='num-endereco'>" + numeroEndereco + "</span></label> "+
            "<div class='form-group'> "+
            "    <div class='col-xs-12'> "+
            "        <input type='text' class='form-control' id='cep-" + numeroEndereco + "' placeholder='CEP...'> "+
            "    </div> "+
            "</div> "+
            "<div class='form-group'> "+
            "    <div class='col-xs-12'> "+
            "        <input type='text' class='form-control' id='endereco-" + numeroEndereco + "' placeholder='Endereço...'> "+
            "    </div> "+
            "</div> "+
            "<div class='form-group'> "+
            "    <div class='col-xs-12'> "+
            "        <input type='text' class='form-control' id='complemento-" + numeroEndereco + "' placeholder='Complemento...'> "+
            "    </div> "+
            "</div> "+
            "<div class='form-group'> "+
            "    <div class='col-xs-12'> "+
            "        <input type='text' class='form-control' id='bairro-" + numeroEndereco + "' placeholder='Bairro...'> "+
            "    </div> "+
            "</div> "+
            "<div class='form-group'> "+
            "    <div class='col-xs-12'> "+
            "        <input type='text' class='form-control' id='cidade-" + numeroEndereco + "' placeholder='Cidade...'> "+
            "    </div> "+
            "</div> "+
            "<div class='form-group'> "+
            "    <div class='col-xs-12'> "+
            "        <input type='text' class='form-control' id='estado-" + numeroEndereco + "' placeholder='Estado...'> "+
            "    </div> "+
            "</div> "+
            " <button id='btn-cancelar' type='button' class='btn btn-danger save-card'> "+
            "    <span class='glyphicon glyphicon-remove' aria-hidden='true'></span> "+
            "</button><br> "+
        "</div>");
    });
}

function process_action(psid)
{
    $('button#btn-enviar').on('click', function (e){
        if($(this).hasClass('nosubmit'))
        {
            e.preventDefault();
            return false;
        }
        $(this).addClass('nosubmit');
    });
    $.extend(
        $.validator.messages, {
            required: 'Campo obrigatório.',
        }
    );
    setup_cad_endereco(psid);
}

function error_handler(err)
{
    $('#lista-enderecos').html('Desculpe, mas não consegui recuperar seus endereços, por favor, refaça o login e tente novamente.');
}