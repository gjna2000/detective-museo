% Caso: robo de la Copa de Oro (sala de trofeos, 8:00 p. m.)
:- encoding(utf8).
:- discontiguous huella/2.

ficha(director,     'Aurelio Montoya', 'Director del museo').
ficha(guardia,      'Hernán Ríos',     'Guardia de seguridad').
ficha(restauradora, 'Lucía Paredes',   'Restauradora').
ficha(guia,         'Tomás Vega',      'Guía turístico').
ficha(donante,      'Isabela Cortés',  'Donante').
ficha(conserje,     'Ramiro Castaño',  'Conserje').

persona(director).
persona(guardia).
persona(restauradora).
persona(guia).
persona(donante).
persona(conserje).

objeto_robado(copa_de_oro, sala_trofeos).
hora_robo(20).
conectada(bodega, sala_trofeos).

estuvo_en(guardia, sala_trofeos, 19).
estuvo_en(guardia, entrada, 20).
estuvo_en(conserje, bodega, 19).
estuvo_en(conserje, sala_trofeos, 20).
estuvo_en(guia, entrada, 20).
estuvo_en(director, oficina, 20).
estuvo_en(restauradora, bodega, 20).
estuvo_en(donante, entrada, 19).
estuvo_en(donante, entrada, 20).

tiene_llave(guardia, sala_trofeos).
tiene_llave(director, sala_trofeos).
tiene_llave(conserje, bodega).
tiene_llave(restauradora, bodega).

motivo(conserje, deuda).
motivo(donante, rencor).
motivo(guia, ambicion).

coartada(director, restauradora).
coartada(guia, donante).

declaro_estar(conserje, bodega, 20).
declaro_estar(guardia, entrada, 20).

testigo_vio(guardia, conserje, sala_trofeos, 20).
huella(conserje, vitrina).

conoce_valor(conserje).
conoce_valor(director).
conoce_valor(guardia).
conoce_valor(restauradora).
experto_seguridad(guardia).
experto_seguridad(director).
sabe_horario_guardia(conserje).
sabe_horario_guardia(guia).

relacion(conserje, guia, amigos).

huella(guardia, vitrina).

uniforme(guardia).
uniforme(conserje).
uniforme(guia).