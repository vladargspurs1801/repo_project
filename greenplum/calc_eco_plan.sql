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
							and pr.proname = 'calc_eco_plan'
						)
		loop
		  	execute del_command;
		end loop;
end $$;

/*
Эта функция (хранимая процедура) выполняет заполнение таблицы juke_custom.eco_product_report отчетом по реализации эко-продуктов по следующим показателям:
1. Фактическая сумма реализации.
2. Сумма плана.
3. Процент выполнения плана.
4. Рейтинг магазина в зависимости от выполнения плана.
Описание источников:
1. juke_custom.eco_product_sales => это таблица, которая содержит информацию о фактической реализации эко-продуктов каждым магазином в разрезе сегментов. Агрегация выполняется по дням. Необходимо собрать факты
за квартал. Для этого предварительно вычисляется первый и последний день квартала относительно переданного аргумента-даты p_date.
2. juke_custom.shop_directory => это справочник, содержащий наименование каждого магазина в соответствии с его ID.
3. juke_custom.shop_plan => это таблица, которая содержит планы по реализации эко-продуктов.
Описание целевой таблицы:
1. juke_custom.eco_product_report => это таблица в схеме (далее в слое) stg.1 Она содержит только данные за текущий квартал относительно начала расчета (переданного аргумента p_date). Перед каждым выполнением расчета таблица
полностью очищается. Далее эта таблица служит источником для заполнения другой целевой таблицы, расположенной в слое core.2 Выбор в пользу использования таблиц в слое stg сделан по причине большого кол-ва видов продуктов.
Это сделает заполнение основной целевой таблицы в слое core более лаконичным.

Примечание:
1. stg - это слой для промежуточных таблиц.
2. core - это слой для основных целевых таблиц.
3. Заполнение основной целевой таблицы, расположенной в слое core, выполняется через insert ... select ... Я не стал приводить это в качестве примера. 
*/

CREATE OR REPLACE FUNCTION juke_custom.calc_eco_plan(p_date date, p_id bigint)
RETURNS void
LANGUAGE plpgsql
VOLATILE
AS $$

declare
	
	/*
	  developer_name - dd.mm.yyyy: заполнили план, факт, выполнение плана и рейтинг.
	*/
	
	l_msgtext text;
	l_oper_name varchar(1024) := 'Расчет показателей по эко-продуктам';
	l_context text;
	l_arguments jsonb;
	l_calc_stats jsonb;
	last_day_qrt date := cast(date_trunc('quarter', p_date) + interval '3 months' - interval '1 day' as date); -- конец текущего квартала
	first_day_qrt date := date_trunc('quarter', p_date)::date; -- первый день текущего квартала;
	l_ins int8 := 0;
	
begin
	-- для логгирования
	l_msgtext := clock_timestamp() || ' ' || 'Запуск функции ' || l_oper_name ||'E\n';
	get diagnostics l_context := pg_context;
	
	l_arguments := json_build_object('p_date', p_date)::jsonb;
	
	l_msgtext := l_msgtext || clock_timestamp() || ' ' || 'Подготовка планов, фактов реализации эко-продуктов за дату ' || to_char(p_date, 'dd.mm.yyyy') ||'E\n';
	
	truncate table juke_custom.eco_product_report;
	
	with eco_fact as (
					    select t.shop_name,
							   f.shop_id,
							   round(sum(f.fact_sal)/100,0) as fact_eco
						 from juke_custom.eco_product_sales as f
						 join juke_custom.shop_directory as t on t.shop_id = f.shop_id
						where f.date_report between first_day_qrt and last_day_qrt
						and f.segment in ('small', 'retail')
						group by t.shop_name, f.shop_id
					  ),
		
		eco_plan as (
					  select t.shop_name,
							 p.shop_id,
							 p.plan_sal as plan_eco
					   from juke_custom.shop_plan as p
					   join juke_custom.shop_directory as t on t.shop_id = p.shop_id
					  where p.product_type = 'ECO-PRODUCT'
					),
		
		plan_eco_proc as (
						    select fct.shop_id,
								   fct.shop_name,
								   fct.fact_eco,
								   pln.plan_eco,
								   round( least( (round(sum(fct.fact_eco),0) / nullif(round(sum(pln.plan_eco),0),0) ) * 100, 101), 2) as eco_plan_proc
						     from eco_fact fct
							 left join eco_plan as pln on fct.shop_id = pln.shop_id
							 group by fct.shop_id, fct.shop_name, fct.fact_eco, pln.plan_eco
					     )
		
		insert into juke_custom.eco_product_report
		(
		  date_report,
		  shop_id,
		  shop_name,
		  fact_sale,
		  plan_sale,
		  plan_proc,
		  product_type,
		  plan_rang
		)
		select p_date as date_report,
			   ecp.shop_id,
			   ecp.shop_name,
			   ecp.fact_eco as fact_sale,
			   ecp.plan_eco as plan_sale,
			   ecp.eco_plan_proc as plan_proc,
			   'ECO-PRODUCT' as product_type,
			   dense_rank() over (order by ecp.eco_plan_proc desc) as plan_rang
	     from plan_eco_proc ecp;
		
		get diagnostics l_ins := row_count;
		
		l_msgtext := l_msgtext || clock_timestamp() || ' ' || 'Завершение расчета показателей по эко-продуктам.' ||'E\n';
		
		l_calc_stats := json_build_object('p_ins', l_ins)::jsonb;
		
		perform juke_custom.logs_insert(p_oper_name := l_oper_name, p_context := l_context, p_arg := l_arguments, p_info := 'I', p_message := l_msgtext, p_load_id := p_id, p_stats := l_calc_stats);

exception
	when others then
		get stacked diagnostics l_context = pg_exception_context;
		l_msgtext := l_msgtext || clock_timestamp() || ' ' ||E' Операция \''|| l_oper_name || ' завершилась с ошибкой. Error code ' || sqlstate || '. Error: ' || sqlerrm || '. Context: ' || l_context;
		perform juke_custom.logs_insert(p_oper_name := l_oper_name, p_context := l_context, p_arg := l_arguments, p_info := 'E', p_message := l_msgtext, p_load_id := p_id, p_stats := l_calc_stats);
end;
$$
EXECUTE ON ANY;