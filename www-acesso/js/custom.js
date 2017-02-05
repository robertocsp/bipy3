//var base_url = 'https://sistema.marviin.com.br';
var base_url = 'http://localhost:8888';
function generateUUID() {
    var d = new Date().getTime();
    if(window.performance && typeof window.performance.now === "function"){
        d += performance.now(); //use high-precision timer if available
    }
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random()*16)%16 | 0;
        d = Math.floor(d/16);
        return (c=='x' ? r : (r&0x3|0x8)).toString(16);
    });
    return uuid;
}

function try_json_parse(data, empty_message){
    try {
        var json = JSON.parse(data);
        if(typeof(data) === 'string')
            if(data.length === 0)
                if(empty_message)
                    return {valid: false, value: empty_message};
                else
                    return {valid: false, value: ''};
        return {valid: true, value: json};
    }
    catch(e){
        return {valid: false, value: data};
    }
}

function get_error_json(data){
    var error_json;
    if(data.responseText){
        var call_return = try_json_parse(data.responseText);
        if(call_return.valid){
            var error = try_json_parse(call_return.value.message);
            if(error.valid && error.value){
                error_json = error.value;
            }
        }
    }
    return error_json;
}

function alert_error(data, my_error_json){
    var error_message;
    var error_json = my_error_json ? my_error_json : get_error_json(data);
    if(error_json && error_json.object){
        error_message = error_json.object;
    }
    if (!error_message)
        error_message = 'Erro inesperado, tente novamente em instantes. Caso o erro continue, por favor, entre em contato conosco para informar o ocorrido. Obrigado!';
    alert(error_message);
}

function verifica_cnpj(cnpj){
	var cnpj = cnpj.replace(/\D+/g, '');
	if (cnpj.length !== 14)
	    return false;
	var tamanho = 13
	var numeros = cnpj.substring(0,tamanho);
	var digitos = cnpj.substring(tamanho-1);
	var soma1 = 0;
	var soma2 = 0;
	var pos = 6;
	for (i = tamanho; i >= 1; i--){
		soma2 += numeros.charAt(tamanho - i) * pos--;
		if(i > 1)
			soma1 += numeros.charAt(tamanho - i) * (pos > 1 ? pos : 9);
		if (pos < 2)
			pos = 9;
	}
	var resto1 = soma1 % 11;
	var dv1 = resto1 < 2 ? 0 : 11 - resto1;
	var resto2 = soma2 % 11;
	var dv2 = resto2 < 2 ? 0 : 11 - resto2;
	if (digitos !== dv1 + '' + dv2)
		return false;
	return true;
}

function preencheValoresCidade(cidade)
{
    $("#cidade_estabelecimento").html('');
    if (cidade.length > 1)
    {
        $("#cidade_estabelecimento")
                    .append($('<option>', { value : '' })
                    .attr('disabled', 'disabled')
                    .attr('selected', 'selected')
                    .text('Selecione'));
    }
    $.each(cidade, function(i, cidades) {
        var nome = cidades.nome;
        var id = cidades.id;
        $("#cidade_estabelecimento")
                    .append($('<option>', { value : id })
                    .text(nome));
    });
}

function preencheValoresCep(endereco, complemento, bairro, estado, cidade)
{
    $("#endereco_estabelecimento").fadeOut(500);
    $("#complemento_estabelecimento").fadeOut(500);
    $("#bairro_estabelecimento").fadeOut(500);
    $("#estado_estabelecimento").fadeOut(500);
    $("#cidade_estabelecimento").fadeOut(500);

    if (endereco === '')
    {
        $("#endereco_estabelecimento").removeProp('readonly');
        $("#bairro_estabelecimento").removeProp('readonly');
        $("#estado_estabelecimento").removeProp('readonly');
        $("#cidade_estabelecimento").removeProp('readonly');
    }
    else
    {
        $("#endereco_estabelecimento").prop('readonly', true);
        $("#bairro_estabelecimento").prop('readonly', true);
        $("#estado_estabelecimento").prop('readonly', true);
        $("#cidade_estabelecimento").prop('readonly', true);
    }

    $("#endereco_estabelecimento").val(endereco);
    $("#complemento_estabelecimento").val(complemento);
    $("#bairro_estabelecimento").val(bairro);
    $("#estado_estabelecimento").html('');
    if (estado.length > 1)
    {
        $("#estado_estabelecimento")
                    .append($('<option>', { value : '' })
                    .attr('disabled', 'disabled')
                    .attr('selected', 'selected')
                    .text('Selecione'));
    }
    $.each(estado, function(i, estados) {
        var nome = estados.nome;
        var id = estados.id;
        $("#estado_estabelecimento")
                    .append($('<option>', { value : id })
                    .text(nome));
    });
    preencheValoresCidade(cidade);

    $("#endereco_estabelecimento").fadeIn(500);
    $("#complemento_estabelecimento").fadeIn(500);
    $("#bairro_estabelecimento").fadeIn(500);
    $("#estado_estabelecimento").fadeIn(500);
    $("#cidade_estabelecimento").fadeIn(500);
}

$(function() {
    if ($('#permissao-pagina')[0])
    {
        setup_solicitacao_acesso();
        var checa_todos_erros = function() {
            var form = $( this );

            var marca_erros = function() {
                form.find('.invalid-field').each( function( index, node ) {
                    $(node).removeClass('invalid-field');
                });
                form.find( ":invalid" ).each( function( index, node ) {
                    $(node).addClass('invalid-field');
                });
                if ($('#tipo_cadastro_usuario').val() === '') {
                    $('#btn_tenho_login').addClass('invalid-field');
                    $('#btn_nao_tenho_login').addClass('invalid-field');
                } else {
                    $('#btn_tenho_login').removeClass('invalid-field');
                    $('#btn_nao_tenho_login').removeClass('invalid-field');
                }
            };

            var form_solicitacao_acesso_function =  function( event ) {
                var form = $( this );
                if ( form[0].checkValidity && !form[0].checkValidity() ) {
                    form.find( ':invalid' ).first().focus();
                    event.preventDefault();
                } else if ($('#tipo_cadastro_usuario').val() === '') {
                    form.find('button').focus();
                    event.preventDefault();
                } else {
                    form.off('submit');
                    $('div.loading-marviin').show();
                    $.post(base_url + '/marviin/api/rest/acesso_bot_v3', form.serialize(),
                             function(data) {
                               console.log(data);
//                               form[0].reset();
                               alert(data.message);
//                               location.reload();
                             },
                             'json'
                    )
                    .fail(function(data) {
                        console.log(data);
                        alert_error(data);
                    })
                    .always(function() {
                        $('div.loading-marviin').hide();
                        form.on('submit', form_solicitacao_acesso_function);
                    });
                }
            };
            form.on( 'submit', form_solicitacao_acesso_function);

            $( 'input[type=submit], button:not([type=button])', form )
                .on( 'click', marca_erros);

            $( 'input', form ).on( 'keypress', function( event ) {
                var type = $( this ).attr( 'type' );
                if ( /date|email|month|number|search|tel|text|time|url|week/.test ( type )
                  && event.keyCode == 13 ) {
                    marca_erros();
                }
            });
        };
        $('#form_solicitacao_acesso').each(checa_todos_erros);

        function setup_solicitacao_acesso()
        {
            $('#btn_estabelecimento_existente').hide();
            $('.novo_estabelecimento, .novo_estabelecimento_campo').hide();
            $('.novo_estabelecimento_campo').prop('disabled', true);

            var SPMaskBehavior = function (val) {
              return val.replace(/\D/g, '').length === 11 ? '(00) 00000-0000' : '(00) 0000-00009';
            },
            spOptions = {
              onKeyPress: function(val, e, field, options) {
                  field.mask(SPMaskBehavior.apply({}, arguments), options);
              }
            };

            $('#cnpj_estabelecimento').mask('00.000.000/0000-00');
            $('#tel_estabelecimento').mask(SPMaskBehavior, spOptions);
            $('#tel_usuario').mask(SPMaskBehavior, spOptions);
            $('#cep_estabelecimento').mask('00000-000');

            $('#cnpj_estabelecimento').blur(function() {
                if(this.setCustomValidity) {
                    if(!verifica_cnpj($(this).val())) {
                        this.setCustomValidity('CNPJ inválido.');
                    } else {
                        this.setCustomValidity('');
                    }
                }
            });

            $("#cep_estabelecimento").blur(function() {

                //Nova variável "cep" somente com dígitos.
                var cep = $(this).val().replace(/\D/g, '');

                //Verifica se campo cep possui valor informado.
                if (cep != '') {

                    //Expressão regular para validar o CEP.
                    var validacep = /^[0-9]{8}$/;

                    //Valida o formato do CEP.
                    if(validacep.test(cep)) {

                        //Consulta o webservice viacep.com.br/
                        $.getJSON("//viacep.com.br/ws/"+ cep +"/json/?callback=?", function(dados) {

                            if (!("erro" in dados)) {
                                //Atualiza os campos com os valores da consulta.
                                var uf = [{'id': dados.uf, 'nome': dados.uf}];
                                var cidade = [{'id': dados.localidade, 'nome': dados.localidade}];
                                preencheValoresCep(dados.logradouro, '', dados.bairro, uf, cidade);
                            } //end if.
                            else {
                                //CEP pesquisado não foi encontrado.
                                $.getJSON(base_url + '/marviin/api/rest/estados', function(dados) {
                                    preencheValoresCep('', '', '', dados.estados, []);
                                });
                            }
                        });
                    } //end if.
                    else {
                        //cep é inválido.
                        preencheValoresCep('', '', '', [], []);
                        alert("Formato de CEP inválido.");
                    }
                } //end if.
                else {
                    //cep sem valor, limpa formulário.
                    preencheValoresCep('', '', '', [], []);
                }
            });

            $('#estado_estabelecimento').change(function(){
                $.getJSON(base_url + '/marviin/api/rest/cidades?estado='+$(this).val(), function(dados) {
                    $("#cidade_estabelecimento").fadeOut(500);
                    preencheValoresCidade(dados.cidades);
                    $("#cidade_estabelecimento").fadeIn(500);
                });
            });

            $('#btn_novo_estabelecimento').on('click', function(){
                $('#btn_novo_estabelecimento').hide();
                $('#btn_estabelecimento_existente').show();
                $('.novo_estabelecimento, .novo_estabelecimento_campo').show();
                $('.novo_estabelecimento_campo').prop('disabled', false);
            });

            $('#btn_estabelecimento_existente').on('click', function(){
                $('#btn_novo_estabelecimento').show();
                $('#btn_estabelecimento_existente').hide();
                $('.novo_estabelecimento, .novo_estabelecimento_campo').hide();
                $('.novo_estabelecimento_campo').prop('disabled', true);
            });

            $('#btn_tenho_login').on('click', function(){
                if($('.novo_estabelecimento_campo').prop('disabled'))
                {
                    $('#btn_novo_estabelecimento').show();
                    $('#btn_estabelecimento_existente').hide();
                }
                else
                {
                    $('#btn_novo_estabelecimento').hide();
                    $('#btn_estabelecimento_existente').show();
                }
                $('#tipo_cadastro_usuario').val(1);
                $('#nao_tenho_login').hide();
                $('#tenho_login').show();
                $('#login_usuario').prop('required', true);
                $('#senha_usuario').prop('required', true);
                $('#nome_usuario').removeProp('required');
                $('#nome_usuario').removeClass('invalid-field');
                $('#nome_usuario').val('');
                $('#sobrenome_usuario').removeClass('invalid-field');
                $('#sobrenome_usuario').val('');
                $('#email_usuario').removeProp('required');
                $('#email_usuario').removeClass('invalid-field');
                $('#email_usuario').val('');
                $('#tel_usuario').removeProp('required');
                $('#tel_usuario').removeClass('invalid-field');
                $('#tel_usuario').val('');
            });

            $('#btn_nao_tenho_login').on('click', function(){
                $('#btn_novo_estabelecimento').hide();
                $('#btn_estabelecimento_existente').hide();
                $('.novo_estabelecimento, .novo_estabelecimento_campo').show();
                $('.novo_estabelecimento_campo').prop('disabled', false);
                $('#tipo_cadastro_usuario').val(2);
                $('#tenho_login').hide();
                $('#nao_tenho_login').show();
                $('#nome_usuario').prop('required', true);
                $('#email_usuario').prop('required', true);
                $('#tel_usuario').prop('required', true);
                $('#login_usuario').removeProp('required');
                $('#login_usuario').removeClass('invalid-field');
                $('#login_usuario').val('');
                $('#senha_usuario').removeProp('required');
                $('#senha_usuario').removeClass('invalid-field');
                $('#senha_usuario').val('');
            });

            $('a.esqueci-senha').on('click', function(e){
                var $this = $(this);
                e.preventDefault();
                if($this.hasClass('nosubmit'))
                    return;
                $this.addClass('nosubmit');

                var fieldValidation = $(this).parent().parent().find('input[type=email]');
                if((!!fieldValidation[0].checkValidity && !fieldValidation[0].checkValidity()) ||
                    $.trim(fieldValidation.val()) === ''){
                    fieldValidation.addClass('invalid-field');
                    fieldValidation.focus();
                    $this.removeClass('nosubmit');
                    return;
                }

                $('div.loading-marviin').show();
                $.post(base_url + '/marviin/api/rest/esqueci_senha',
                     {email: fieldValidation.val()},
                     function(data) {
                       console.log(data);
                       $this.removeClass('nosubmit');
                       alert(data.message);
                     },
                     'json'
                )
                .fail(function(data) {
                    console.log(data);
                    alert_error(data);
                })
                .always(function() {
                    $('div.loading-marviin').hide();
                });
            });
        }
    }

    if ($('#secao_campos_senha')[0])
    {
        var data = {};
        var token = $.url().param('token');
        var token2 = $.url().param('token2');
        if(!!token)
            data['token'] = token;
        else if(!!token2)
            data['token2'] = token2;
        $('div.loading-marviin').show();
        $.post(base_url + '/marviin/api/rest/valida_token',
                 data,
                 function(data) {
                   $('#secao_campos_senha').html(data);
                   var form = $('#form_cadastro_senha');
                   var campo_senha = form.find('input[name=senha]');
                   var campo_confirma_senha = form.find('input[name=confirma_senha]');

                   function valida_senha(senha) {
                        var senha = campo_senha.val();
                        return (senha && senha.length >= 6
                                && /[A-Z]/.test(senha)
                                && /[a-z]/.test(senha)
                                && /\d/.test(senha)
                                && /[^a-zA-Z\d]/.test(senha));
                   }

                   function valida_confirma_senha(element) {
                        var senha = campo_senha.val();
                        var confirma_senha = campo_confirma_senha.val();
                        if (senha !== confirma_senha)
                            element.setCustomValidity('A senha de confirmação não confere com a senha digitada.');
                        else
                            element.setCustomValidity('');
                   }

                   campo_senha.on('keyup', function() {
                        if(this.setCustomValidity && !valida_senha())
                            this.setCustomValidity('Para sua segurança sua senha deve possuir pelo menos 6 caracteres, dentre eles, 1 caractere especial, 1 número, 1 letra minúscula e 1 letra maiúscula.');
                        else
                            this.setCustomValidity('');
                        if(campo_confirma_senha[0].setCustomValidity)
                            valida_confirma_senha(campo_confirma_senha[0])
                   });

                   campo_confirma_senha.on('keyup', function() {
                        if(this.setCustomValidity)
                            valida_confirma_senha(this)
                   });

                   form.find('input[name=ver_caracteres]').on('click', function() {
                        if ($(this).prop('checked'))
                            form.find('input[type=password]').attr('type', 'text');
                        else
                            form.find('input[type=text]').attr('type', 'password');
                   });

                   var form_cria_senha_function = function(event){
                        if ( form[0].checkValidity && !form[0].checkValidity() ) {
                            form.find( ':invalid' ).first().focus();
                            event.preventDefault();
                        } else {
                            form.off('submit');
                            $('div.loading-marviin').show();
                            $.post(base_url + '/marviin/api/rest/'+$('input#metodo').val(),
                                     form.serialize(),
                                     function(data) {
                                       console.log(data);
                                       alert(data.message);
                                       form[0].reset();
                                       window.location.href = '/';
                                     },
                                     'json'
                            )
                            .fail(function(data) {
                                console.log(data);
                                var error_json = get_error_json(data);
                                if(error_json){
                                    if (error_json.type === 'pass1' || error_json.type === 'pass2'){
                                        var element;
                                        if (error_json.type === 'pass1')
                                            element = campo_senha[0];
                                        else
                                            element = campo_confirma_senha[0];
                                        if(element.setCustomValidity){
                                            element.setCustomValidity(error_json.object);
                                            form.submit();
                                            return;
                                        } else {
                                            element.addClass('invalid-field');
                                        }
                                    }
                                }
                                alert_error(data, error_json);
                            })
                            .always(function() {
                                $('div.loading-marviin').hide();
                                form.find('input[type=text]').attr('type', 'password');
                                form.on('submit', form_cria_senha_function);
                            });
                        }
                   };

                   form.on('submit', form_cria_senha_function);
                 },
                 'html'
        )
        .fail(function(data) {
            console.log(data);
            alert_error(data);
        })
        .always(function() {
            $('div.loading-marviin').hide();
        });
    }
});