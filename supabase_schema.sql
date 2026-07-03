-- ----------------------------------------------------
-- IANA - ESQUEMA DE BASE DE DATOS ACTUALIZADO
-- ----------------------------------------------------
-- Implementa:
-- 1. Diferenciación de tipos de proyectos chilenos.
-- 2. Almacenamiento de contexto consolidado del proyecto.
-- 3. Tabla de análisis individuales de documentos (caché).
-- 4. Políticas RLS estrictas.
-- ----------------------------------------------------

DROP TABLE IF EXISTS public.document_analyses CASCADE;
DROP TABLE IF EXISTS public.documents CASCADE;
DROP TABLE IF EXISTS public.projects CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

DO $$ 
BEGIN
    DROP TYPE IF EXISTS public.document_type CASCADE;
    DROP TYPE IF EXISTS public.project_type CASCADE;
    DROP TYPE IF EXISTS public.user_role CASCADE;

    CREATE TYPE public.user_role AS ENUM (
        'architect', 
        'independent_developer', 
        'engineering', 
        'public_admin', 
        'other'
    );
    
    CREATE TYPE public.project_type AS ENUM (
        'private_housing',
        'large_scale_real_estate',
        'public_spaces_green_areas',
        'other'
    );

    CREATE TYPE public.document_type AS ENUM (
        'cip',
        'ett',
        'site_plan',
        'sections',
        'elevations',
        'other'
    );
END $$;

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    rut VARCHAR(20) UNIQUE NOT NULL,
    role public.user_role NOT NULL DEFAULT 'architect',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    project_type public.project_type NOT NULL DEFAULT 'private_housing',
    region VARCHAR(100) NOT NULL,
    commune VARCHAR(100) NOT NULL,
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    terrain_rol VARCHAR(50),
    block VARCHAR(50),
    lot VARCHAR(50),
    
    consolidated_context TEXT DEFAULT 'Proyecto inicializado sin documentos cargados.',
    consolidated_infractions JSONB DEFAULT '[]'::jsonb,
    success_probability NUMERIC(5, 2) DEFAULT 0.0,
    extracted_metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: documents
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    document_type public.document_type NOT NULL,
    bucket_path VARCHAR(512) NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: document_analyses
-- Sirve como memoria y caché de cada archivo
CREATE TABLE IF NOT EXISTS public.document_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    extracted_text_summary TEXT NOT NULL,
    infractions JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_project_id ON public.documents(project_id);
CREATE INDEX IF NOT EXISTS idx_analyses_document_id ON public.document_analyses(document_id);

-- TRIGGER PARA SINCRONIZAR AUTH.USERS CON PUBLIC.USERS
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.users (id, email, name, phone, rut, role)
    VALUES (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'name', ''),
        coalesce(new.raw_user_meta_data->>'phone', ''),
        coalesce(new.raw_user_meta_data->>'rut', ''),
        coalesce((new.raw_user_meta_data->>'role')::public.user_role, 'architect'::public.user_role)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- HABILITAR ROW LEVEL SECURITY (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_analyses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own profile" ON public.users;
CREATE POLICY "Users can view their own profile"
    ON public.users FOR SELECT TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.users;
CREATE POLICY "Users can update their own profile"
    ON public.users FOR UPDATE TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can view their own projects" ON public.projects;
CREATE POLICY "Users can view their own projects"
    ON public.projects FOR SELECT TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create their own projects" ON public.projects;
CREATE POLICY "Users can create their own projects"
    ON public.projects FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own projects" ON public.projects;
CREATE POLICY "Users can update their own projects"
    ON public.projects FOR UPDATE TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own projects" ON public.projects;
CREATE POLICY "Users can delete their own projects"
    ON public.projects FOR DELETE TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view their project documents" ON public.documents;
CREATE POLICY "Users can view their project documents"
    ON public.documents FOR SELECT TO authenticated USING (
        EXISTS (SELECT 1 FROM public.projects WHERE projects.id = documents.project_id AND projects.user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can add documents to their projects" ON public.documents;
CREATE POLICY "Users can add documents to their projects"
    ON public.documents FOR INSERT TO authenticated WITH CHECK (
        EXISTS (SELECT 1 FROM public.projects WHERE projects.id = documents.project_id AND projects.user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can delete documents from their projects" ON public.documents;
CREATE POLICY "Users can delete documents from their projects"
    ON public.documents FOR DELETE TO authenticated USING (
        EXISTS (SELECT 1 FROM public.projects WHERE projects.id = documents.project_id AND projects.user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can view their document analyses" ON public.document_analyses;
CREATE POLICY "Users can view their document analyses"
    ON public.document_analyses FOR SELECT TO authenticated USING (
        EXISTS (
            SELECT 1 FROM public.documents
            JOIN public.projects ON projects.id = documents.project_id
            WHERE documents.id = document_analyses.document_id AND projects.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can create analyses for their documents" ON public.document_analyses;
CREATE POLICY "Users can create analyses for their documents"
    ON public.document_analyses FOR INSERT TO authenticated WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.documents
            JOIN public.projects ON projects.id = documents.project_id
            WHERE documents.id = document_analyses.document_id AND projects.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Allow users to upload project files" ON storage.objects;
CREATE POLICY "Allow users to upload project files" 
    ON storage.objects FOR INSERT TO authenticated 
    WITH CHECK (
        bucket_id = 'project-documents' 
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

DROP POLICY IF EXISTS "Allow users to read their own project files" ON storage.objects;
CREATE POLICY "Allow users to read their own project files" 
    ON storage.objects FOR SELECT TO authenticated 
    USING (
        bucket_id = 'project-documents' 
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

DROP POLICY IF EXISTS "Allow users to delete their own project files" ON storage.objects;
CREATE POLICY "Allow users to delete their own project files" 
    ON storage.objects FOR DELETE TO authenticated 
    USING (
        bucket_id = 'project-documents' 
        AND (storage.foldername(name))[1] = auth.uid()::text
    );