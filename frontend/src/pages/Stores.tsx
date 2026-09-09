import { useState, FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

interface Store {
  id: number;
  name: string;
  code: string;
}

export default function Stores() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  const { data: stores, isLoading } = useQuery({
    queryKey: ["stores"],
    queryFn: async () => (await api.get<Store[]>("/stores")).data,
  });

  const createStore = useMutation({
    mutationFn: (payload: { name: string; code: string }) => api.post("/stores", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stores"] });
      setName("");
      setCode("");
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    createStore.mutate({ name, code });
  }

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>المتاجر</h1>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <input
          placeholder="اسم المتجر"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          placeholder="كود المتجر (مثال: store_1)"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
        <button type="submit" disabled={createStore.isPending}>
          إضافة
        </button>
      </form>

      {isLoading ? (
        <p>...جار التحميل</p>
      ) : (
        <ul>
          {stores?.map((store) => (
            <li key={store.id}>
              <Link to={`/stores/${store.id}/invoices`}>
                {store.name} ({store.code})
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
