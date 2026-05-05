#!/bin/bash
# Instala pipeline skills no Cursor local
# Uso: ./scripts/install-pipeline-skills.sh

set -e

SKILLS_DIR="$HOME/.cursor/skills"
REPO_SKILLS_DIR="$(dirname "$0")/../skills"

echo "📦 Instalando pipeline skills do Dev Pipeline Orchestrator..."
echo ""

# Verificar se diretório de skills do Cursor existe
if [ ! -d "$SKILLS_DIR" ]; then
    echo "⚠️  Diretório ~/.cursor/skills não existe. Criando..."
    mkdir -p "$SKILLS_DIR"
fi

# Verificar se skills do repo existem
if [ ! -d "$REPO_SKILLS_DIR" ]; then
    echo "❌ Erro: Diretório skills/ não encontrado no repo."
    echo "   Certifique-se de estar executando do diretório raiz do projeto."
    exit 1
fi

# Contar skills instaladas
INSTALLED=0
SKIPPED=0
UPDATED=0

for skill in "$REPO_SKILLS_DIR"/pipeline-*; do
    if [ ! -d "$skill" ]; then
        continue
    fi
    
    skill_name=$(basename "$skill")
    target="$SKILLS_DIR/$skill_name"
    
    if [ -d "$target" ]; then
        # Skill já existe, perguntar se quer atualizar
        echo "⚠️  $skill_name já existe."
        read -p "   Deseja sobrescrever? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$target"
            cp -r "$skill" "$SKILLS_DIR/"
            echo "✅ $skill_name atualizada"
            UPDATED=$((UPDATED + 1))
        else
            echo "⏭️  $skill_name mantida (não atualizada)"
            SKIPPED=$((SKIPPED + 1))
        fi
    else
        echo "✅ Instalando $skill_name..."
        cp -r "$skill" "$SKILLS_DIR/"
        INSTALLED=$((INSTALLED + 1))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Instalação concluída!"
echo ""
echo "📊 Resumo:"
echo "   - Instaladas: $INSTALLED"
echo "   - Atualizadas: $UPDATED"
echo "   - Mantidas: $SKIPPED"
echo ""
echo "🔍 Skills disponíveis em ~/.cursor/skills/:"
ls -1 "$SKILLS_DIR"/pipeline-* 2>/dev/null | sed 's|.*/||' | sed 's/^/   - /'
echo ""
echo "📖 Próximos passos:"
echo "   1. Configure .env com suas credenciais"
echo "   2. Execute: make dev-pipeline STORY=<PROJECT>-XXXX"
echo ""
echo "   Documentação: docs/dev-pipeline-guide.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
