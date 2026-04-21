create or replace function f_get_kpk_muk(p_date date, p_gosb number, p_descrip varchar2) return varchar2
is

	l_date date := trunc(p_date);
	l_descrip varchar2(2000) := p_descrip;
	return_kpk varchar2(100);

begin

	with descrip_kpk as
   (
     select replace(replace(regexp_substr(l_descrip, '#\w\d+', 1, level), '#'),'v') as kpk
	  from dual
	 where regexp_like(l_descrip, '#\w\d+')
	 connect by
	 level <= regexp_count(l_descrip, '#\w\d+')
	 and prior sys_guid() is not null
   )
   
   select t.kpk
   into return_kpk
    from descrip_kpk t
    join spr_departments m on t.kpk = m.dep
   where m.gosb = p_gosb
   and m.month = to_char(l_date, 'yyyym')
   fetch first 1 rows only;
   
   return return_kpk;

end f_get_kpk_muk;