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
        onfocusout: false,
        onkeyup: false,
        onclick: false
    });
}

function process_action(psid)
{
    alert(psid);
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