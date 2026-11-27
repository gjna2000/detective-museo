:- encoding(utf8).
% servidor.pl - Detective del Museo (interfaz web)
% Uso:  cd src   y luego   swipl servidor.pl   -> abrir http://localhost:8080

:- use_module(library(http/thread_httpd)).
:- use_module(library(http/http_dispatch)).
:- use_module(library(http/http_json)).
:- use_module(library(http/http_parameters)).

:- [hechos, reglas, preguntas].

:- prolog_load_context(directory, D), assertz(dir_base(D)).

:- http_handler(root(.),              inicio,         []).
:- http_handler(root(api/personas),   api_personas,   []).
:- http_handler(root(api/escena),     api_escena,     []).
:- http_handler(root(api/huella),     api_huella,     []).
:- http_handler(root(api/interrogar), api_interrogar, []).
:- http_handler(root(api/acusar),     api_acusar,     []).
:- http_handler(root(api/preguntar),  api_preguntar,  []).

servidor :-
    http_server(http_dispatch, [port(8080)]),
    format('~nJuego listo. Abre en el navegador: http://localhost:8080~n').

:- initialization(servidor).

inicio(Request) :-
    dir_base(D),
    directory_file_path(D, 'index.html', F),
    http_reply_file(F, [unsafe(true)], Request).

api_personas(_) :-
    findall(_{id: P, nombre: N, cargo: C}, ficha(P, N, C), Lista),
    reply_json_dict(Lista).

api_escena(_) :-
    reply_json_dict(_{pistas: [
        'La vitrina está abierta, sin señales de fuerza.',
        'Hay una huella parcial en el cristal (sin analizar).',
        'La puerta de la bodega estaba sin seguro.'
    ]}).

api_huella(_) :-
    findall(P, huella(P, vitrina), Lista),
    reply_json_dict(_{coincidencias: Lista,
                      aviso: 'Una huella no prueba un robo: compara con las versiones.'}).

api_interrogar(Request) :-
    http_parameters(Request, [persona(P, [atom])]),
    (   persona(P)
    ->  hora_robo(H),
        (   declaro_estar(P, S, H) -> true
        ;   estuvo_en(P, S, H)     -> true
        ;   S = desconocida
        ),
        ( coartada(P, T) -> true ; T = null ),
        ( uniforme(P) -> U = true ; U = false ),
        (   testigo_vio(P, _, Sv, Hv)
        ->  Test = _{hora: Hv, sala: Sv}
        ;   Test = null
        ),
        reply_json_dict(_{persona: P, hora: H, ubicacion: S,
                          coartada: T, uniforme: U, testimonio: Test})
    ;   reply_json_dict(_{error: 'Persona desconocida'}, [status(404)])
    ).

api_acusar(Request) :-
    http_parameters(Request, [persona(P, [atom])]),
    (   persona(P)
    ->  once(culpable(C)),
        (   P == C
        ->  Ok = true, Msg = ''
        ;   Ok = false, mensaje_error(P, Msg)
        ),
        findall(R, razon(C, R), Razones),
        ranking(Ranking),
        reply_json_dict(_{persona: P, correcto: Ok, mensaje: Msg,
                          culpable: C, razones: Razones, ranking: Ranking})
    ;   reply_json_dict(_{error: 'Persona desconocida'}, [status(404)])
    ).

mensaje_error(P, 'No tenía motivo ni una conducta sospechosa. Revisa a otros.') :-
    descartado(P), !.
mensaje_error(_, 'Tiene algunos indicios, pero no reúne motivo, medios y oportunidad.').

razon(P, 'Tenía una deuda (motivo).')                :- deuda_economica(P).
razon(P, 'Tenía acceso a la sala de trofeos.')       :- tenia_acceso(P).
razon(P, 'Conocía el valor de la copa.')             :- conocia_el_valor(P).
razon(P, 'Estuvo en la escena a la hora del robo.')  :- estuvo_en_escena(P).
razon(P, 'Mintió sobre dónde estaba.')               :- mintio(P).
razon(P, 'Dejó su huella en la vitrina.')            :- huella_en_vitrina(P).
razon(P, 'Un testigo lo vio en la sala.')            :- testigo_lo_vio(P).

ranking(Lista) :-
    findall(N-P, puntaje_sospecha(P, N), Pares),
    sort(0, @>=, Pares, Orden),
    findall(_{persona: P, puntaje: N}, member(N-P, Orden), Lista).

api_preguntar(Request) :-
    http_parameters(Request, [persona(P, [atom]), texto(Txt, [])]),
    (   persona(P)
    ->  responder(P, Txt, Intenciones, Respuesta),
        reply_json_dict(_{persona: P, intenciones: Intenciones, respuesta: Respuesta})
    ;   reply_json_dict(_{error: 'Persona desconocida'}, [status(404)])
    ).