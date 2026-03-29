import { useState, useEffect } from 'react';
import { supabase } from '../utils/supabase';

export interface SupabaseTodo {
  id: number;
  name: string;
  created_at: string;
}

export function useSupabaseTodos() {
  const [todos, setTodos] = useState<SupabaseTodo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function getTodos() {
      if (!supabase) {
        setError('Supabase not configured. Please create .env file with VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY');
        setLoading(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from('todos')
          .select('*');
        
        if (error) throw error;
        setTodos(data || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch todos');
      } finally {
        setLoading(false);
      }
    }

    getTodos();
  }, []);

  const addTodo = async (name: string) => {
    if (!supabase) {
      setError('Supabase not configured');
      return;
    }

    try {
      const { data, error } = await supabase
        .from('todos')
        .insert([{ name }])
        .select();
      
      if (error) throw error;
      setTodos(prev => [...prev, ...(data || [])]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add todo');
    }
  };

  const deleteTodo = async (id: number) => {
    if (!supabase) {
      setError('Supabase not configured');
      return;
    }

    try {
      const { error } = await supabase
        .from('todos')
        .delete()
        .eq('id', id);
      
      if (error) throw error;
      setTodos(prev => prev.filter(todo => todo.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete todo');
    }
  };

  return { todos, loading, error, addTodo, deleteTodo };
}
