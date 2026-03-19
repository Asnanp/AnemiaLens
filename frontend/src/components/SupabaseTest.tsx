import { useSupabaseTodos } from '../hooks/useSupabaseTodos';

export function SupabaseTest() {
  const { todos, loading, error, addTodo, deleteTodo } = useSupabaseTodos();

  if (loading) return <div>Loading todos...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div style={{ padding: '2rem', background: 'rgba(255,255,255,0.05)', borderRadius: '1rem', margin: '2rem' }}>
      <h3>Supabase Test</h3>
      <ul>
        {todos.map((todo) => (
          <li key={todo.id}>
            {todo.name}
            <button 
              onClick={() => deleteTodo(todo.id)}
              style={{ marginLeft: '1rem', padding: '0.25rem 0.5rem' }}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
      <button 
        onClick={() => addTodo(`Test todo ${Date.now()}`)}
        style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}
      >
        Add Test Todo
      </button>
    </div>
  );
}
