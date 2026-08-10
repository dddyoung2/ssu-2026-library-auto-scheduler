GRANT select on public.test_students to anon;
GRANT select on public.test_students to service_role;
grant select, insert on public.test_students TO authenticated;