import ast
import operator
from typing import Any, Dict, List, Tuple, Callable

class Rule:
    """
    Represents a single compliance rule.
    
    Attributes:
        name (str): The unique name of the rule.
        description (str): A human-readable description of the rule.
        rule_algo (str): A string representing the rule logic.
    """
    def __init__(self, name: str, description: str, rule_algo: str):
        self.name = name
        self.description = description
        self.rule_algo = rule_algo

class ComplianceReport:
    """
    Represents the result of a compliance check.
    
    Attributes:
        item (Dict[str, Any]): The original data item (e.g., a shipment).
        passed (bool): Whether the item passed all the rules.
        violated_rules (List[str]): Names of the rules that were not satisfied.
    """
    def __init__(self, item: Dict[str, Any], passed: bool, violated_rules: List[str] = None):
        self.item = item
        self.passed = passed
        self.violated_rules = violated_rules or []

class RuleEvaluator:
    """
    Evaluates a rule string safely using AST parsing.
    """
    # Map AST operator nodes to actual operations
    OPERATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    @classmethod
    def evaluate(cls, rule_str: str, context: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Safely evaluate the rule string within the given context.
        Returns a tuple: (overall_result, list_of_violation_details).
        """
        # Create a safe evaluation namespace: allow only a few built-in functions
        safe_namespace = context.copy()
        safe_namespace.update({
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'any': any,
            'all': all,
            # Provide a keys() function to return the keys of the current data item.
            'keys': lambda: list(context.keys()),
        })

        violations: List[Dict[str, Any]] = []
        try:
            # Parse the rule into an AST expression
            tree = ast.parse(rule_str, mode='eval')
            result = cls._eval_node(tree.body, safe_namespace, violations)
            return result, violations
        except Exception as e:
            violations.append({"error": str(e), "expression": rule_str})
            return False, violations

    @classmethod
    def _eval_node(cls, node: ast.AST, namespace: Dict[str, Any], violations: List[Dict[str, Any]]) -> Any:
        """
        Recursively evaluate an AST node in the given namespace.
        """
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                results = [cls._eval_node(value, namespace, violations) for value in node.values]
                return all(results)
            elif isinstance(node.op, ast.Or):
                results = [cls._eval_node(value, namespace, violations) for value in node.values]
                return any(results)
            else:
                raise ValueError(f"Unsupported boolean operator: {node.op}")
        elif isinstance(node, ast.Compare):
            left = cls._eval_node(node.left, namespace, violations)
            result = True
            # Handle chained comparisons like a < b < c
            for op, comparator in zip(node.ops, node.comparators):
                right = cls._eval_node(comparator, namespace, violations)
                op_func: Callable = cls.OPERATORS.get(type(op))
                if op_func is None:
                    raise ValueError(f"Unsupported operator: {op}")
                if not op_func(left, right):
                    result = False
                    violations.append({
                        "expression": ast.unparse(node).strip(),
                        "left": left,
                        "operator": ast.unparse(op).strip(),
                        "right": right,
                    })
                    break
                left = right  # for chain comparisons
            return result
        
        elif isinstance(node, ast.GeneratorExp):
            # Support for a single generator expression
            gen_exp = node
            # Evaluate the iterable part of the generator (e.g., "for code in ...")
            iter_obj = cls._eval_node(gen_exp.generators[0].iter, namespace, violations)
            target = gen_exp.generators[0].target.id  # assumes simple variable target
            def generator():
                for item in iter_obj:
                    # Create a new namespace for each iteration with the loop variable set
                    local_ns = namespace.copy()
                    local_ns[target] = item
                    yield cls._eval_node(gen_exp.elt, local_ns, violations)
            return generator()

        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not cls._eval_node(node.operand, namespace, violations)
            else:
                raise ValueError(f"Unsupported unary operator: {node.op}")
        elif isinstance(node, ast.Name):
            if node.id in namespace:
                return namespace[node.id]
            else:
                raise ValueError(f"Unknown variable: {node.id}")
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Call):
            # Only allow calls to safe functions provided in the namespace.
            func = cls._eval_node(node.func, namespace, violations)
            args = [cls._eval_node(arg, namespace, violations) for arg in node.args]
            kwargs = {kw.arg: cls._eval_node(kw.value, namespace, violations) for kw in node.keywords}
            return func(*args, **kwargs)
        elif isinstance(node, ast.List):
            return [cls._eval_node(elt, namespace, violations) for elt in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(cls._eval_node(elt, namespace, violations) for elt in node.elts)
        elif isinstance(node, ast.Dict):
            return {cls._eval_node(key, namespace, violations): cls._eval_node(value, namespace, violations)
                    for key, value in zip(node.keys, node.values)}
        else:
            # As a fallback, compile and evaluate the node in the safe namespace.
            try:
                code = compile(ast.Expression(node), "<ast>", "eval")
                return eval(code, {"__builtins__": {}}, namespace)
            except Exception as e:
                raise ValueError(f"Unsupported expression: {ast.unparse(node).strip()}: {e}")

class RuleEngine:
    """
    A rule engine that checks items against a set of rules.
    """
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def check(self, item: Dict[str, Any]) -> ComplianceReport:
        """
        Checks a single item against all rules and returns a ComplianceReport.
        """
        violated_rule_names = []
        for rule in self.rules:
            passed, _ = RuleEvaluator.evaluate(rule.rule_algo, item)
            if not passed:
                violated_rule_names.append(rule.name)
        return ComplianceReport(item=item, passed=(len(violated_rule_names) == 0),
                                violated_rules=violated_rule_names)

    def batch_check(self, items: List[Dict[str, Any]]) -> List[ComplianceReport]:
        """
        Checks a list of items and returns a list of ComplianceReports.
        """
        return [self.check(item) for item in items]

# === Example Usage ===

def main():
    # Define some sample rules.
    rules = [
        Rule(
            name="Restricted Country",
            description="Shipment must not be sent to restricted countries.",
            rule_algo="destination_country not in ['Iran', 'Cuba', 'North Korea', 'Russia', 'Syria']"
        ),
        Rule(
            name="High Value Without License",
            description="High value shipments (declared_value > 5000) must include an export license.",
            rule_algo="declared_value <= 5000 or 'export_license' in keys()"
        ),
        Rule(
            name="Commodity Code Check",
            description="Certain commodity codes require special clearance.",
            rule_algo="not any(code in commodity_codes for code in ['930690', '854231', '300490', '123456' , '710812'])"
        )
    ]

    # Create the rule engine instance.
    engine = RuleEngine(rules)

    # Sample shipment items.
    shipments = [
        {
            "destination_country": "Iran",
            "declared_value": 6000,
            "commodity_codes": ["930690", "123456"],
            # keys() function in rule will return the keys of this dictionary.
        },
        {
            "destination_country": "USA",
            "declared_value": 4000,
            "commodity_codes": ["123456"],
        },
        {
            "destination_country": "Germany",
            "declared_value": 7500,
            "commodity_codes": ["710811"],
            "export_license": "LICENSE123",
        }
    ]

    # Process shipments.
    reports = engine.batch_check(shipments)

    # Output the compliance reports.
    for report in reports:
        print("Shipment Data:", report.item)
        print("Compliance:", "Passed" if report.passed else "Failed")
        if not report.passed:
            print("Violated Rules:", report.violated_rules)
        print("-" * 40)

if __name__ == "__main__":
    main()
