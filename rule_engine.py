import ast
import operator
from typing import Any, Dict, List, Tuple, Protocol
from schemas import Violation, ConsignmentStatus

class RuleInterface(Protocol):
    """Protocol defining the required attributes for a Rule"""
    id: str
    name: str
    description: str
    condition: str
    status: str

class Rule:
    """Rule class that can be used independently of the database"""
    def __init__(self, id: str, name: str, description: str, condition: str):
        self.id = id
        self.name = name
        self.description = description
        self.condition = condition
        self.status = 'active'

class RuleEvaluator:
    """Evaluates rule conditions safely using AST parsing"""
    
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
        Returns a tuple: (overall_result, list_of_violation_details)
        """
        safe_namespace = context.copy()
        safe_namespace.update({
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'any': any,
            'all': all,
            'keys': lambda: list(context.keys()),
        })

        violations: List[Dict[str, Any]] = []
        try:
            tree = ast.parse(rule_str, mode='eval')
            result = cls._eval_node(tree.body, safe_namespace, violations)
            return result, violations
        except Exception as e:
            violations.append({"error": str(e), "expression": rule_str})
            return False, violations

    @classmethod
    def _eval_node(cls, node: ast.AST, namespace: Dict[str, Any], violations: List[Dict[str, Any]]) -> Any:
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
            for op, comparator in zip(node.ops, node.comparators):
                right = cls._eval_node(comparator, namespace, violations)
                op_func = cls.OPERATORS.get(type(op))
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
                left = right
            return result
        elif isinstance(node, (ast.Constant, ast.Num, ast.Str, ast.NameConstant)):
            return node.value if hasattr(node, 'value') else node.n
        elif isinstance(node, ast.Name):
            if node.id in namespace:
                return namespace[node.id]
            else:
                raise ValueError(f"Unknown variable: {node.id}")
        elif isinstance(node, ast.List):
            return [cls._eval_node(elt, namespace, violations) for elt in node.elts]
        else:
            raise ValueError(f"Unsupported expression: {ast.unparse(node).strip()}")

class ComplianceEngine:
    """Engine for checking compliance against a set of rules"""
    
    def __init__(self, rules: List[RuleInterface]):
        """Initialize with a list of rules that implement RuleInterface"""
        self.rules = [rule for rule in rules if rule.status == 'active']

    def check_compliance(self, consignment_data: Dict[str, Any]) -> Tuple[ConsignmentStatus, List[Violation]]:
        """
        Check a consignment against all active rules.
        Returns a tuple of (status, violations).
        """
        violations: List[Violation] = []
        
        for rule in self.rules:
            passed, violation_details = RuleEvaluator.evaluate(rule.condition, consignment_data)
            if not passed:
                violations.append(
                    Violation(
                        rule_id=str(rule.id),
                        description=rule.description,
                        condition_str=rule.condition,
                        resolution_steps=f"Please check that your consignment complies with the following rule: {violation_details}"
                    )
                )

        status = ConsignmentStatus.VERIFIED if not violations else ConsignmentStatus.FLAGGED
        return status, violations 