const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

const tokenTypes = ['function', 'variable', 'parameter', 'type', 'class'];
const tokenModifiers = ['declaration', 'readonly'];
const legend = new vscode.SemanticTokensLegend(tokenTypes, tokenModifiers);

const KAA_MODIFIERS_MAP = {
    '-i': 'integer',
    '-f': 'float',
    '-s': 'string',
    '-l': 'list',
    '-t': 'tuple',
    '-d': 'dict',
    '-py': 'python',
    '-obj': 'object',
    '-T': 'true',
    '-F': 'false'
};

// ─── Lista EXATA do que está implementado na VM/Interpretador ───────────────

// Atributos universais: funcionam em qualquer tipo
const KAA_UNIVERSAL_ATTRS = ['is_num', 'length', 'rm_nil', 'f_valuation'];

// Atributos de string: apenas os que foram programados
const KAA_STRING_ATTRS = ['capitalize', 'capitalize_phrase', 'upper_letters', 'lower_letters', 'replace_elements'];

// Atributos de dicionário: além dos universais
const KAA_DICT_ATTRS = ['keys', 'values'];

// Todos os métodos implementados (para coleções que podem ter qualquer tipo)
const KAA_ALL_ATTRS = [...new Set([...KAA_UNIVERSAL_ATTRS, ...KAA_STRING_ATTRS, ...KAA_DICT_ATTRS])];

// Mapeamento por tipo de variável
const KAA_TYPES_METHODS = {
    'integer': KAA_UNIVERSAL_ATTRS,
    'float':   KAA_UNIVERSAL_ATTRS,
    'string':  [...KAA_UNIVERSAL_ATTRS, ...KAA_STRING_ATTRS],
    // coleções: acesso a tudo pois podem armazenar texto e números
    'list':    KAA_ALL_ATTRS,
    'dict':    KAA_ALL_ATTRS,
    'tuple':   KAA_ALL_ATTRS,
    'object':  KAA_ALL_ATTRS,
    'python':  KAA_UNIVERSAL_ATTRS,
    'true':    KAA_UNIVERSAL_ATTRS,
    'false':   KAA_UNIVERSAL_ATTRS
};

class DocumentSemanticTokensProvider {
    async provideDocumentSemanticTokens(document, token) {
        const tokensBuilder = new vscode.SemanticTokensBuilder(legend);
        const text = document.getText();
        
        // Find all variable declarations
        // TextMate uses entity.name.function.kaa for variables declared with var
        const varDeclRegex = /\bvar\b(?:\s+-(?:i|f|s|l|t|d|py|obj|T|F)\b)?\s+([a-zA-Z_]\w*)/g;
        const declaredVars = new Set();
        let match;
        while ((match = varDeclRegex.exec(text)) !== null) {
            declaredVars.add(match[1]);
        }

        // Add fun declarations too so they stay highlighted the same
        const funDeclRegex = /\bfun\s+([a-zA-Z_]\w*)/g;
        while ((match = funDeclRegex.exec(text)) !== null) {
            declaredVars.add(match[1]);
        }

        const lines = text.split('\n');
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const wordRegex = /\b([a-zA-Z_]\w*)\b/g;
            while ((match = wordRegex.exec(line)) !== null) {
                const word = match[1];
                if (declaredVars.has(word)) {
                    // Start position
                    const startCharacter = match.index;
                    // Provide token 'function' (index 0) → mesma cor de entity.name.function.kaa (atributos)
                    tokensBuilder.push(
                        i, startCharacter, word.length, 0, 0 // 0 = 'function', mesma cor de alunos.length
                    );
                }
            }
        }
        return tokensBuilder.build();
    }
}

class KaaCompletionItemProvider {
    provideCompletionItems(document, position, token, context) {
        const linePrefix = document.lineAt(position).text.substr(0, position.character);
        const completionItems = [];

        // 1. Module exports (add "module" -> )
        const moduleImportMatch = linePrefix.match(/add\s+"([^"]+)"\s*->\s*([^;]*)$/);
        if (moduleImportMatch) {
            const moduleName = moduleImportMatch[1];
            // Resolve workspace folder
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders) {
                const root = workspaceFolders[0].uri.fsPath;
                const libPath = path.join(root, 'libs', moduleName + '.kaa');
                if (fs.existsSync(libPath)) {
                    const content = fs.readFileSync(libPath, 'utf-8');
                    const exporMatch = content.match(/expor\s+([^;]+);/);
                    if (exporMatch) {
                        const exports = exporMatch[1].split(',').map(e => e.trim());
                        for (const exp of exports) {
                            const item = new vscode.CompletionItem(exp, vscode.CompletionItemKind.Function);
                            // Se for a última importação, o usuário digita ';', mas vamos sugerir no snippet
                            item.insertText = new vscode.SnippetString(exp);
                            completionItems.push(item);
                        }
                    }
                }
            }
            return completionItems;
        }

        // 2. Variable attributes (varName.)
        const varMatch = linePrefix.match(/\b([a-zA-Z_]\w*)\.$/);
        if (varMatch) {
            const varName = varMatch[1];
            const text = document.getText();
            
            // Find declaration
            const escapedVarName = varName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const declRegex = new RegExp(`\\bvar\\b(?:\\s+(-(?:i|f|s|l|t|d|py|obj|T|F))\\b)?\\s+${escapedVarName}\\b`);
            const match = text.match(declRegex);
            
            let varType = 'generic'; // default
            if (match && match[1]) {
                const modifier = match[1].trim();
                if (KAA_MODIFIERS_MAP[modifier]) {
                    varType = KAA_MODIFIERS_MAP[modifier];
                }
            }

            let methodsToSuggest = new Set();

            if (varType === 'generic') {
                // Tipo não declarado: sugere apenas atributos universais
                KAA_UNIVERSAL_ATTRS.forEach(m => methodsToSuggest.add(m));
            } else {
                // Apenas os métodos do tipo específico (já incluem os universais relevantes)
                const specificMethods = KAA_TYPES_METHODS[varType] || [];
                specificMethods.forEach(m => methodsToSuggest.add(m));
                // Sempre inclui is_num pois está implementado para qualquer objeto na VM
                methodsToSuggest.add('is_num');
            }
            
            // Atributos: acesso como propriedade, sem parênteses
            const ATTR_STYLE = new Set([
                'length', 'keys', 'values', 'rm_nil', 'f_valuation', 'is_num'
            ]);
            // Métodos: acesso com parênteses
            const METHOD_STYLE = new Set([
                'capitalize', 'capitalize_phrase', 'upper_letters', 'lower_letters', 'replace_elements'
            ]);

            for (const method of methodsToSuggest) {
                const item = new vscode.CompletionItem(method, vscode.CompletionItemKind.Method);
                if (ATTR_STYLE.has(method)) {
                    item.insertText = new vscode.SnippetString(`${method};`);
                    item.detail = '(atributo) → sem parênteses';
                } else if (METHOD_STYLE.has(method)) {
                    item.insertText = new vscode.SnippetString(`${method}(\${1});`);
                    item.detail = '(método) → com parênteses';
                } else {
                    item.insertText = new vscode.SnippetString(`${method}(\${1});`);
                    item.detail = '(método)';
                }
                completionItems.push(item);
            }
            
            return completionItems;
        }
        
        return undefined;
    }
}

function activate(context) {
    const selector = { language: 'kaa', scheme: 'file' };

    context.subscriptions.push(
        vscode.languages.registerDocumentSemanticTokensProvider(
            selector,
            new DocumentSemanticTokensProvider(),
            legend
        )
    );

    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            selector,
            new KaaCompletionItemProvider(),
            '>', '.' // trigger characters
        )
    );
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
