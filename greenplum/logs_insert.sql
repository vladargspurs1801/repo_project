do $$
declare
	del_command text;
begin
	for del_command in (
							select format('drop function if exists %s.%s(%s);',
										   ns.nspname,
										   pr.proname,
										   oidvectortypes(pr.proargtypes)
										 )
							 from pg_proc as pr
							 join pg_namespace as ns on pr.pronamespace = ns.oid
							where ns.nspname = 'juke_custom'
							and pr.proname = 'logs_insert'
						)
		loop
		  	execute del_command;
		end loop;
end $$;

/*
Эта функция (хранимая процедура) выполняется для реализации логирования.
Отличить записи логирования можно по идентификатору (столбцу info_log).
'I' - информация о текущем выполнении функции без ошибок.
'E' - информация об ошибке. 
*/

CREATE OR REPLACE FUNCTION juke_custom.logs_insert(
	p_oper_name varchar,
	p_context varchar,
	p_info varchar,
	p_message text,
	p_load_id int8,
	p_stats jsonb DEFAULT NULL::jsonb,
	p_log_date date DEFAULT clock_timestamp(),
	p_arg jsonb DEFAULT NULL::jsonb)
    RETURNS void
    LANGUAGE plpgsql
    VOLATILE
AS $$

declare
	
	/*
	  developer_name - dd.mm.yyyy: реализовали логгирование.
	*/
	l_context text;
begin

	insert into juke_custom.logger_table
	(
	  oper_name,
	  context,
	  args,
	  info_log,
	  message_log,
	  load_oper,
	  dml_stat,
	  oper_date
	)
	values (p_oper_name, p_context, p_arg, p_info, p_message, p_load_id, p_stats, p_log_date);

exception
	when others then
		get stacked diagnostics l_context = pg_exception_context;
		raise exception E'\nЛогирование завершилось с ошибкой: \ncode: % \nerror: % \ncontext: %', sqlstate, sqlerrm, l_context;
end;
$$
EXECUTE ON ANY;