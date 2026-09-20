
"use client";
import { useState, useEffect } from "react";

export default function Home() {
  const [acesso, setAcesso] = useState(false);
  const [senha, setSenha] = useState("");
  const [bilhetes, setBilhetes] = useState<any[]>([]);

  const jogos = [
    { casa: "Flamengo", fora: "Palmeiras", palpite: "Dupla Chance Flamengo", odd: 1.45 },
    { casa: "Real Madrid", fora: "Barcelona", palpite: "Mais de 1.5 Gols", odd: 1.35 },
    { casa: "Man City", fora: "Arsenal", palpite: "City marca", odd: 1.40 },
    { casa: "Brasil", fora: "Argentina", palpite: "Ambas marcam - Não", odd: 1.80 },
    { casa: "PSG", fora: "Bayern", palpite: "+7.5 Escanteios", odd: 1.70 },
  ];

  const gerar = () => {
    const b = [...jogos].sort(() => 0.5 - Math.random());
    setBilhetes([
      { nome: "BILHETE SIMPLES", desc: "Para dobrar a banca", odd: "2.15", jogos: [b[0]], cor: "bg-green-600" },
      { nome: "BILHETE ODD 10x", desc: "Equilibrado", odd: "10.80", jogos: [b[0], b[1], b[2]], cor: "bg-blue-600" },
      { nome: "BILHETE ODD 50x", desc: "O da forra", odd: "50.45", jogos: [b[0], b[1], b[2], b[3]], cor: "bg-gradient-to-r from-purple-600 to-pink-600" },
    ]);
  };

  useEffect(() => { gerar(); }, []);

  if (!acesso) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-4">
        <div className="bg-zinc-900 p-8 rounded-xl w-full max-w-sm">
          <h1 className="text-white text-2xl font-bold text-center">FUTBET</h1>
          <p className="text-zinc-400 text-center mb-4 text-sm">3 Análises Diárias</p>
          <input type="password" placeholder="Senha" className="w-full p-3 rounded bg-zinc-800 text-white mb-4" value={senha} onChange={e=>setSenha(e.target.value)} />
          <button onClick={()=> senha==="futbet2026"? setAcesso(true) : alert("Senha errada")} className="w-full bg-green-600 p-3 rounded text-white font-bold">ENTRAR</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-4 max-w-md mx-auto">
      <h1 className="text-center font-bold mb-4">FUTBET - {new Date().toLocaleDateString()}</h1>
      {bilhetes.map((b,i)=>(
        <div key={i} className={`${b.cor} p-4 rounded-xl mb-4`}>
          <div className="flex justify-between"><b>{b.nome}</b><span className="bg-black px-2 rounded">{b.odd}x</span></div>
          <p className="text-xs opacity-80 mb-2">{b.desc}</p>
          {b.jogos.map((j:any,k:number)=><div key={k} className="bg-black/40 p-2 rounded mb-1 text-sm">{j.casa} x {j.fora} - {j.palpite}</div>)}
        </div>
      ))}
      <button onClick={gerar} className="w-full bg-zinc-800 p-3 rounded mt-2">🔄 Atualizar Bilhetes</button>
    </div>
  );
}
